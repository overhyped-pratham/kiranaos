import json
import re
from typing import Dict, Any, List, Optional
import httpx
from backend.app.config import settings

class LLMService:
    def __init__(self):
        self.model = settings.LLM_MODEL
        self.hf_key = settings.HUGGINGFACE_API_KEY
        self.openai_key = settings.OPENAI_API_KEY
        self.groq_key = settings.GROQ_API_KEY
        self.provider = settings.LLM_PROVIDER

    def parse_customer_intent(self, message: str) -> Dict[str, Any]:
        """
        Parses customer natural language into structured intent and item queries.
        Supports English, Hindi, and Hinglish.
        Uses hosted LLM (Qwen2.5-3B-Instruct) when API key is available,
        with seamless fallback to deterministic semantic extractor.
        """
        # Try external LLM API if configured
        if self.provider != "local":
            external_res = self._try_external_llm(message)
            if external_res:
                return external_res

        # Fallback to high-precision multilingual Kirana language parser
        return self._local_semantic_parser(message)

    def _try_external_llm(self, message: str) -> Optional[Dict[str, Any]]:
        """Call Qwen2.5-3B-Instruct via HuggingFace Inference API or OpenAI/Groq compatible endpoints."""
        prompt = f"""You are KiranaOS Language Understanding Engine.
Analyze this grocery message from a customer in India (English / Hindi / Hinglish):
"{message}"

Extract strictly valid JSON with this schema:
{{
  "intent": "create_order" | "repeat_usual" | "inquire" | "cancel",
  "items": [
    {{
      "product_query": "name of product or brand",
      "quantity": int (default 1),
      "size_hint": "5kg" | "1L" | null
    }}
  ],
  "delivery_required": true | false,
  "address": null | string,
  "confidence": float
}}
DO NOT guess prices or stock. Output JSON only, no markdown."""

        # 1. HuggingFace Inference API
        if self.hf_key:
            try:
                url = f"https://api-inference.huggingface.co/models/{self.model}"
                headers = {"Authorization": f"Bearer {self.hf_key}", "Content-Type": "application/json"}
                payload = {
                    "inputs": prompt,
                    "parameters": {"max_new_tokens": 300, "temperature": 0.1, "return_full_text": False}
                }
                with httpx.Client(timeout=5.0) as client:
                    resp = client.post(url, headers=headers, json=payload)
                    if resp.status_code == 200:
                        text = resp.json()[0].get("generated_text", "")
                        return self._clean_and_parse_json(text)
            except Exception:
                pass

        # 2. Groq API
        if self.groq_key:
            try:
                url = "https://api.groq.com/openai/v1/chat/completions"
                headers = {"Authorization": f"Bearer {self.groq_key}", "Content-Type": "application/json"}
                payload = {
                    "model": "qwen-2.5-32b",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"}
                }
                with httpx.Client(timeout=5.0) as client:
                    resp = client.post(url, headers=headers, json=payload)
                    if resp.status_code == 200:
                        content = resp.json()["choices"][0]["message"]["content"]
                        return json.loads(content)
            except Exception:
                pass

        return None

    def _clean_and_parse_json(self, raw_text: str) -> Optional[Dict[str, Any]]:
        try:
            cleaned = re.sub(r"^```(?:json)?", "", raw_text.strip())
            cleaned = re.sub(r"```$", "", cleaned.strip())
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                return json.loads(match.group(0))
        except Exception:
            return None
        return None

    def _local_semantic_parser(self, message: str) -> Dict[str, Any]:
        """
        Deterministic, robust semantic parser for Hinglish, Hindi, and English grocery syntax.
        Handles phrases like:
        - 'Hi bhaiya, 2 packets Aashirvaad atta, 1 Fortune oil aur 3 Maggi bhej do. Ghar pe deliver kar dena.'
        - 'bhaiya mera usual samaan bhej do'
        - 'wo 5 kilo wala aata bhej dena'
        - '2 atta, 1 oil aur 3 maggi ghar bhej do'
        - '50 Fortune oil bhej do'
        """
        msg_lower = message.lower().strip()

        # Check for repeat/usual order intent
        if any(term in msg_lower for term in [
            "usual", "pichli baar", "pichla saman", "pichla samaan", "purana order", "repeat order", "vahi samaan", "wahi saman", "wahi samaan"
        ]):
            return {
                "intent": "repeat_usual",
                "items": [],
                "delivery_required": True,
                "address": None,
                "confidence": 0.95
            }

        # Check delivery keywords
        delivery_terms = [
            "deliver", "delivery", "bhej", "ghar", "home", "send", "de dena",
            "bhejo", "bhejna", "भेज", "घर", "पहुंचा"
        ]
        delivery_required = any(term in msg_lower for term in delivery_terms)

        # Hindi quantity words mapping (Latin & Devanagari)
        HINDI_NUMS = {
            "ek": 1, "एक": 1, "१": 1,
            "do": 2, "दो": 2, "२": 2,
            "teen": 3, "तीन": 3, "३": 3,
            "char": 4, "chaar": 4, "चार": 4, "४": 4,
            "paanch": 5, "panch": 5, "पांच": 5, "पाँच": 5, "५": 5,
            "chhe": 6, "che": 6, "छह": 6, "६": 6,
            "saat": 7, "सात": 7, "७": 7,
            "aath": 8, "आठ": 8, "८": 8,
            "nau": 9, "नौ": 9, "९": 9,
            "das": 10, "दस": 10, "१०": 10,
            "bees": 20, "बीस": 20,
            "pachaas": 50, "pachas": 50, "पचास": 50
        }

        VERB_PHRASES = [
            r"\b(?:bhej\s*do|de\s*do|kar\s*do|laa?\s*do|rakh\s*do|bata\s*do|bta\s*do|mangwa\s*do|pack\s*kar\s*do)\b",
            r"(?:^|[\s,])(?:भेज\s*दो|दे\s*दो|कर\s*दो|ला\s*दो|रख\s*दो|बता\s*दो|मंगवा\s*दो)(?:[\s,]|$)",
            r"\b(?:deliver\s*kar\s*dena|deliver\s*karo|deliver\s*kardo|deliver\s*karna)\b",
            r"\b(?:bhejo|bhejna|dena|de\s*dena|chahiye|laao|mangwao|bhejiye|dijiye)\b",
            r"(?:^|[\s,])(?:भेजो|भेजना|देना|चाहिए|लाओ|भेजिए|दीजिए)(?:[\s,]|$)"
        ]

        PRONOUNS_AND_FILLERS = [
            r"\b(?:hi|hello|hey|namaste|pranam)\b",
            r"\b(?:bhaiya|bhai|sahab|saheb|ji|uncle|aunty)\b",
            r"\b(?:please|kripya|kripya\s*karke|zara|kindly)\b",
            r"\b(?:wo|woh|yeh|ye|mera|meri|mere|apna|apni|apne)\b",
            r"(?:^|[\s,])(?:वो|वह|ये|यह|मेरा|मेरी|मेरे|कृपया|जरा)(?:[\s,]|$)",
            r"\b(?:ghar\s*pe|ghar\s*par|home|pahuche|pahuncha\s*dena)\b",
            r"(?:^|[\s,])(?:घर\s*पर|घर\s*पे)(?:[\s,]|$)"
        ]

        UNITS = r"\b(?:packet|packets?|pouch|pouches|bottle|bottles?|piece|pieces?|pc|pcs|dabba|dappe|kilo|kg|gm|g|gram|grams|litre|liter|litres|liters|l|ml)\b"

        # Split message into clauses by commas, 'aur', 'and', '&', '+'
        clauses = re.split(r"[,+&]|(?:\s+(?:aur|and|tatha|or)\s+)", message)
        items = []

        for raw_clause in clauses:
            raw_clause = raw_clause.strip()
            if not raw_clause:
                continue

            c = " " + raw_clause + " "

            # 1. Clean compound verb phrases before quantity extraction (e.g. 'bhej do', 'de do')
            for vp in VERB_PHRASES:
                c = re.sub(vp, " ", c, flags=re.IGNORECASE)

            # 2. Clean pronouns and conversational fillers (e.g. 'wo', 'woh', 'bhaiya')
            for pf in PRONOUNS_AND_FILLERS:
                c = re.sub(pf, " ", c, flags=re.IGNORECASE)

            # 3. Check for standalone trailing 'do' or 'दो' (e.g. 'maggi do' -> imperative verb 'give')
            c = re.sub(r"(?<=\s)(?:do|दो)\s*$", " ", c.strip(), flags=re.IGNORECASE)

            c = re.sub(r"\s+", " ", c).strip()
            if not c:
                continue

            # 4. Extract size hint (e.g., 5kg, 10kg, 1L, 500gm)
            size_hint = None
            size_match = re.search(r"\b(\d+)\s*(kilo|kg|l|litre|liter|gm|g|ml)\b", c, re.IGNORECASE)
            if size_match:
                size_hint = size_match.group(0).lower().replace("kilo", "kg").replace(" ", "")
                c_for_qty = c[:size_match.start()] + " " + c[size_match.end():]
            else:
                c_for_qty = c

            # 5. Extract quantity (default: 1)
            qty = 1
            num_match = re.search(r"\b([0-9]+)\b", c_for_qty)
            if num_match:
                qty = int(num_match.group(1))
                c_clean = c_for_qty[:num_match.start()] + " " + c_for_qty[num_match.end():]
            else:
                found_num = False
                for word, val in HINDI_NUMS.items():
                    if re.match(r"^[a-zA-Z0-9]+$", word):
                        pattern = rf"\b{word}\b"
                    else:
                        pattern = rf"(?:^|[\s,]){re.escape(word)}(?:[\s,]|$)"
                    m = re.search(pattern, c_for_qty, re.IGNORECASE)
                    if m:
                        qty = val
                        c_clean = c_for_qty[:m.start()] + " " + c_for_qty[m.end():]
                        found_num = True
                        break
                if not found_num:
                    c_clean = c_for_qty

            # 6. Clean units and grammatical particles from product name
            c_clean = re.sub(UNITS, " ", c_clean, flags=re.IGNORECASE)
            c_clean = re.sub(r"\b(?:wala|wali|wale|ka|ki|ke)\b", " ", c_clean, flags=re.IGNORECASE)
            c_clean = re.sub(r"\s+", " ", c_clean).strip()

            if c_clean and len(c_clean) > 1:
                items.append({
                    "product_query": c_clean,
                    "quantity": qty,
                    "size_hint": size_hint
                })

        # Fallback if items empty: check for known staples
        if not items:
            known_brands = ["atta", "aata", "oil", "tel", "maggi", "noodles", "milk", "doodh", "surf excel", "ariel", "salt", "namak", "biscuit", "soap", "sabun"]
            for brand in known_brands:
                if brand in msg_lower:
                    items.append({
                        "product_query": brand,
                        "quantity": 1,
                        "size_hint": None
                    })

        return {
            "intent": "create_order" if items else "inquire",
            "items": items,
            "delivery_required": delivery_required,
            "address": None,
            "confidence": 0.88 if items else 0.40
        }

llm_service = LLMService()
