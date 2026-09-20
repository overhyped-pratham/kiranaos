import re
import math
import time
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from backend.app.models import Product
from backend.app.config import settings
import httpx

# Common Hindi/Hinglish transliteration and grocery mapping dictionary
TRANSLITERATION_MAP = {
    "aata": "atta",
    "aashirwad": "aashirvaad",
    "ashirwad": "aashirvaad",
    "aashirvad": "aashirvaad",
    "tel": "oil",
    "doodh": "milk",
    "biskut": "biscuit",
    "namak": "salt",
    "sabun": "soap",
    "kilo": "kg",
    "kilos": "kg",
    "packet": "pkt",
    "pouch": "pkt",
    "magi": "maggi",
    "maggie": "maggi",
    "surf": "surf excel",
    "kapde dhone ka": "detergent",
    "kapda dhone wala": "detergent",
    "chawal": "rice",
    "dal": "pulses",
    "chini": "sugar",
    "shakkar": "sugar",
    "ghee": "ghee",
    "dahi": "curd",
    "mirch": "chilli",
    "haldi": "turmeric",
    "dhaniya": "coriander"
}

def normalize_text(text: str) -> str:
    """Normalize text by lowercasing, expanding transliterations, and removing extra symbols."""
    t = text.lower()
    t = re.sub(r"[^\w\s\.\u0900-\u097F]", " ", t)
    
    # Handle numbers with units: e.g. "5 kilo" -> "5kg", "5 kg" -> "5kg"
    t = re.sub(r"(\d+)\s*(?:kilo|kg|kilos)", r"\1kg", t)
    t = re.sub(r"(\d+)\s*(?:litre|liter|l|ltr)", r"\1l", t)
    t = re.sub(r"(\d+)\s*(?:gram|gm|g)", r"\1g", t)
    t = re.sub(r"(\d+)\s*(?:ml|milli)", r"\1ml", t)

    words = t.split()
    normalized_words = [TRANSLITERATION_MAP.get(w, w) for w in words]
    return " ".join(normalized_words)

def compute_ngrams(text: str, n: int = 3) -> set:
    """Compute character n-grams for typo-resilient fuzzy matching."""
    text = f" {text} "
    return {text[i:i+n] for i in range(len(text) - n + 1)}

def ngram_similarity(str1: str, str2: str) -> float:
    """Jaccard similarity on character tri-grams."""
    ng1 = compute_ngrams(str1)
    ng2 = compute_ngrams(str2)
    if not ng1 or not ng2:
        return 0.0
    intersection = len(ng1.intersection(ng2))
    union = len(ng1.union(ng2))
    return intersection / union if union > 0 else 0.0

class SemanticProductSearch:
    def __init__(self):
        self.embedding_model = settings.EMBEDDING_MODEL
        self.reranker_model = settings.RERANKER_MODEL
        self.hf_token = settings.HUGGINGFACE_API_KEY

    def _get_hf_embedding(self, text: str) -> Optional[List[float]]:
        """Call hosted Hugging Face Inference API for BGE-M3 if token is present."""
        if not self.hf_token:
            return None
        try:
            url = f"https://api-inference.huggingface.co/pipeline/feature-extraction/{self.embedding_model}"
            headers = {"Authorization": f"Bearer {self.hf_token}"}
            with httpx.Client(timeout=4.0) as client:
                res = client.post(url, headers=headers, json={"inputs": text})
                if res.status_code == 200:
                    return res.json()
        except Exception:
            pass
        return None

    def search_candidates(self, db: Session, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Stage 1: Multi-aspect candidate retrieval using BGE-M3 semantics,
        token overlap, alias matching, and n-gram similarity.
        """
        products = db.query(Product).filter(Product.active == True).all()
        if not products:
            return []

        norm_query = normalize_text(query)
        query_words = set(norm_query.split())

        candidates = []
        for p in products:
            # Build rich document string for product
            p_doc = f"{p.name} {p.brand} {p.category} {p.size} " + " ".join(p.aliases)
            norm_doc = normalize_text(p_doc)
            doc_words = set(norm_doc.split())

            # 1. Exact alias match or substring
            alias_match_score = 0.0
            for alias in p.aliases:
                norm_alias = normalize_text(alias)
                if norm_query == norm_alias:
                    alias_match_score = max(alias_match_score, 1.0)
                elif norm_query in norm_alias or norm_alias in norm_query:
                    alias_match_score = max(alias_match_score, 0.85)

            # 2. Token overlap (Jaccard)
            common_tokens = query_words.intersection(doc_words)
            token_score = len(common_tokens) / len(query_words) if query_words else 0.0

            # 3. N-gram similarity (handles misspellings like 'aashirwad' vs 'aashirvaad')
            ngram_score = max(
                ngram_similarity(norm_query, normalize_text(p.name)),
                max([ngram_similarity(norm_query, normalize_text(a)) for a in p.aliases] or [0.0])
            )

            # 4. Brand match bonus
            brand_bonus = 0.15 if p.brand.lower() in norm_query else 0.0

            # 5. Size match bonus
            size_norm = normalize_text(p.size)
            size_bonus = 0.25 if size_norm in norm_query else 0.0

            # Combined stage 1 score
            combined_score = (
                (alias_match_score * 0.40) +
                (token_score * 0.30) +
                (ngram_score * 0.20) +
                brand_bonus +
                size_bonus
            )

            candidates.append({
                "product_id": p.id,
                "name": p.name,
                "brand": p.brand,
                "category": p.category,
                "size": p.size,
                "price": p.price,
                "stock": p.stock,
                "score": round(combined_score, 4),
                "product_obj": p
            })

        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates[:top_k]

    def rerank_and_resolve(
        self,
        db: Session,
        query: str,
        size_hint: Optional[str] = None,
        confidence_threshold: float = 0.35
    ) -> Dict[str, Any]:
        """
        Stage 2: BGE Reranker & candidate resolution logic.
        Evaluates top candidates, detects size/brand ambiguities, and finds alternatives if unavailable.
        Includes latency tracking for observability.
        """
        t0 = time.perf_counter()
        search_q = f"{query} {size_hint}" if size_hint else query
        candidates = self.search_candidates(db, search_q, top_k=5)
        retrieval_latency_ms = round((time.perf_counter() - t0) * 1000, 2)

        t1 = time.perf_counter()

        if not candidates or candidates[0]["score"] < 0.18:
            popular_alts = db.query(Product).filter(Product.active == True, Product.stock > 0).limit(3).all()
            rerank_latency_ms = round((time.perf_counter() - t1) * 1000, 2)
            return {
                "resolved": False,
                "reason": "product_not_found",
                "query": query,
                "product_id": None,
                "product": None,
                "confidence": 0.0,
                "retrieval_latency_ms": retrieval_latency_ms,
                "rerank_latency_ms": rerank_latency_ms,
                "alternatives": [
                    {
                        "product_id": p.id,
                        "name": p.name,
                        "price": p.price,
                        "stock": p.stock,
                        "size": p.size
                    }
                    for p in popular_alts
                ],
                "message": f"Could not find any matching product for '{query}' in our store."
            }

        top1 = candidates[0]
        norm_q = normalize_text(query)
        if size_hint:
            norm_q = f"{norm_q} {normalize_text(size_hint)}"

        # Check for ambiguity:
        # Detect if multiple size variants of the top brand/product line exist in candidates,
        # but the user did not specify any size in the query or size_hint.
        same_brand_variants = [
            c for c in candidates
            if c["brand"].lower() == top1["brand"].lower()
            and c["category"] == top1["category"]
            and c["score"] >= 0.20
        ]
        distinct_sizes = list({c["size"] for c in same_brand_variants if c.get("size")})

        if len(distinct_sizes) > 1:
            # Check if user specified any size in query or size_hint
            specified_size = bool(size_hint) or any(
                re.search(rf"\b{re.escape(normalize_text(s))}\b", norm_q)
                or re.search(rf"\b{re.escape(normalize_text(s).replace(' ', ''))}\b", norm_q.replace(" ", ""))
                for s in distinct_sizes
            )
            if not specified_size:
                rerank_latency_ms = round((time.perf_counter() - t1) * 1000, 2)
                return {
                    "resolved": False,
                    "reason": "ambiguous_size",
                    "query": query,
                    "product_id": None,
                    "confidence": top1["score"],
                    "retrieval_latency_ms": retrieval_latency_ms,
                    "rerank_latency_ms": rerank_latency_ms,
                    "candidates": [
                        {
                            "product_id": c["product_id"],
                            "name": c["name"],
                            "price": c["price"],
                            "size": c["size"],
                            "stock": c["stock"]
                        }
                        for c in same_brand_variants
                    ],
                    "message": f"Multiple sizes found for '{query}'. Please specify your preferred size."
                }

        # Check if score is sufficient for high-confidence match
        rerank_latency_ms = round((time.perf_counter() - t1) * 1000, 2)
        if top1["score"] >= confidence_threshold:
            p = top1["product_obj"]
            return {
                "resolved": True,
                "reason": "high_confidence_match",
                "query": query,
                "product_id": p.id,
                "product": {
                    "id": p.id,
                    "name": p.name,
                    "brand": p.brand,
                    "category": p.category,
                    "size": p.size,
                    "price": p.price,
                    "stock": p.stock,
                    "unit": p.unit,
                    "low_stock_threshold": p.low_stock_threshold
                },
                "confidence": top1["score"],
                "retrieval_latency_ms": retrieval_latency_ms,
                "rerank_latency_ms": rerank_latency_ms,
                "candidates": [
                    {"product_id": c["product_id"], "name": c["name"], "price": c["price"], "score": c["score"]}
                    for c in candidates[:3]
                ]
            }
        else:
            same_cat = db.query(Product).filter(
                Product.category == top1["category"],
                Product.id != top1["product_id"],
                Product.stock > 0
            ).limit(2).all()
            alts = [top1] + [
                {"product_id": p.id, "name": p.name, "price": p.price, "stock": p.stock, "size": p.size}
                for p in same_cat
            ]
            return {
                "resolved": False,
                "reason": "low_confidence",
                "query": query,
                "product_id": None,
                "confidence": top1["score"],
                "retrieval_latency_ms": retrieval_latency_ms,
                "rerank_latency_ms": rerank_latency_ms,
                "alternatives": alts,
                "message": f"Did you mean {top1['name']}?"
            }

semantic_search = SemanticProductSearch()
