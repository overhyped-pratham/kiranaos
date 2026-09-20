import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc
from backend.app.models import Customer, Order, OrderItem, CustomerPreference, Product

# Frequently bought together affinities in neighborhood Kirana
FREQUENTLY_BOUGHT_TOGETHER = {
    "prod_maggi_70g": "prod_milk_amul_taaza_500ml",      # Maggi + Milk
    "prod_atta_aashirvaad_5kg": "prod_oil_fortune_1l",   # Atta + Cooking Oil
    "prod_oil_fortune_1l": "prod_salt_tata_1kg",         # Oil + Salt
    "prod_milk_amul_taaza_500ml": "prod_biscuit_parle_g_250g", # Milk + Parle-G
    "prod_surf_excel_1kg": "prod_soap_dettol_75g"        # Surf Excel + Dettol Soap
}

class MemoryService:
    def reconstruct_usual_order(self, db: Session, customer_id: str) -> Dict[str, Any]:
        """
        Reconstructs the customer's usual order based on purchase history and frequency.
        Called when customer asks: 'mera usual samaan bhej do' or 'wahi pichli baar wala'.
        """
        # 1. Fetch preferences ordered by frequency
        prefs = db.query(CustomerPreference).filter(
            CustomerPreference.customer_id == customer_id
        ).order_by(desc(CustomerPreference.frequency)).all()

        if prefs:
            items = []
            for p in prefs:
                prod = db.query(Product).filter(Product.id == p.product_id, Product.active == True).first()
                if prod and prod.stock > 0:
                    items.append({
                        "product_query": prod.name,
                        "product_id": prod.id,
                        "quantity": p.preferred_quantity or 1,
                        "size_hint": prod.size
                    })
            if items:
                return {
                    "success": True,
                    "source": "frequency_profile",
                    "items": items,
                    "message": "Reconstructed from your most frequently ordered groceries."
                }

        # 2. Fallback to last successful order
        last_order = db.query(Order).filter(
            Order.customer_id == customer_id,
            Order.status.in_(["confirmed", "delivered"])
        ).order_by(desc(Order.created_at)).first()

        if last_order and last_order.items:
            items = [
                {
                    "product_query": i.product_name,
                    "product_id": i.product_id,
                    "quantity": i.quantity,
                    "size_hint": None
                }
                for i in last_order.items
            ]
            return {
                "success": True,
                "source": "last_order",
                "items": items,
                "message": f"Reconstructed from your previous order {last_order.id}."
            }

        return {
            "success": False,
            "error": "No previous order history found for this customer.",
            "items": []
        }

    def get_upsell_recommendation(
        self,
        db: Session,
        customer_id: str,
        ordered_product_ids: List[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Generates genuine upsell recommendation based on affinity rules,
        ensuring the recommended product is currently in stock and not already ordered.
        Upselling never blocks the main order.
        """
        candidate_rec_id = None
        for p_id in ordered_product_ids:
            if p_id in FREQUENTLY_BOUGHT_TOGETHER:
                potential = FREQUENTLY_BOUGHT_TOGETHER[p_id]
                if potential not in ordered_product_ids:
                    candidate_rec_id = potential
                    break

        if not candidate_rec_id:
            # Fallback to customer's own top frequent item not in current cart
            pref = db.query(CustomerPreference).filter(
                CustomerPreference.customer_id == customer_id,
                ~CustomerPreference.product_id.in_(ordered_product_ids)
            ).order_by(desc(CustomerPreference.frequency)).first()
            if pref:
                candidate_rec_id = pref.product_id

        if candidate_rec_id:
            prod = db.query(Product).filter(
                Product.id == candidate_rec_id,
                Product.active == True,
                Product.stock > 0
            ).first()
            if prod:
                return {
                    "product_id": prod.id,
                    "name": prod.name,
                    "price": prod.price,
                    "stock": prod.stock,
                    "pitch": f"You may also want {prod.name} (₹{prod.price}), frequently bought together. Add 1 packet?"
                }

        return None

memory_service = MemoryService()
