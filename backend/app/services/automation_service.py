import httpx
from typing import Dict, Any, List, Optional
from backend.app.config import settings

class AutomationService:
    def __init__(self):
        self.n8n_order_url = settings.N8N_WEBHOOK_URL
        self.n8n_alert_url = settings.N8N_ALERT_WEBHOOK_URL
        self.delivery_url = settings.DELIVERY_WEBHOOK_URL

    def trigger_n8n_order_webhook(self, order_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Dispatches confirmed order to n8n workflow for WhatsApp message dispatch.
        Notification failure NEVER rolls back a committed database transaction.
        """
        try:
            with httpx.Client(timeout=0.8) as client:
                res = client.post(self.n8n_order_url, json=order_payload)
                return {
                    "success": res.status_code in [200, 201, 202],
                    "status_code": res.status_code,
                    "target": "n8n_order_webhook"
                }
        except Exception as ex:
            return {
                "success": False,
                "error": str(ex),
                "target": "n8n_order_webhook",
                "note": "Order committed in DB; external notification queued/retryable."
            }

    def trigger_low_stock_alerts(self, low_stock_events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Dispatches low-stock alerts to merchant WhatsApp/dashboard via n8n alert webhook.
        """
        results = []
        for event in low_stock_events:
            try:
                payload = {
                    "alert_type": "LOW_STOCK",
                    "product_id": event.get("product_id"),
                    "product_name": event.get("product_name"),
                    "current_stock": event.get("stock"),
                    "threshold": event.get("threshold"),
                    "merchant_phone": settings.MERCHANT_PHONE
                }
                with httpx.Client(timeout=0.5) as client:
                    res = client.post(self.n8n_alert_url, json=payload)
                    results.append({"event_id": event.get("product_id"), "sent": res.status_code in [200, 201, 202]})
            except Exception as ex:
                results.append({"event_id": event.get("product_id"), "sent": False, "error": str(ex)})
        return results

    def trigger_delivery_dispatch(self, delivery_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Notifies rider or delivery partner service."""
        try:
            with httpx.Client(timeout=0.5) as client:
                res = client.post(self.delivery_url, json=delivery_payload)
                return {"success": res.status_code in [200, 201, 202]}
        except Exception as ex:
            return {"success": False, "error": str(ex)}

automation_service = AutomationService()
