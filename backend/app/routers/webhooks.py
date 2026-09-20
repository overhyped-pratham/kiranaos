import logging
from fastapi import APIRouter, Request, Query, HTTPException, Response, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any
from backend.app.config import settings
from backend.app.agent.graph import run_agent_workflow
from backend.app.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhook", tags=["Webhooks"])

@router.get("/whatsapp")
def verify_whatsapp_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token")
):
    """
    WhatsApp Cloud API Webhook Verification.
    Meta sends GET request with challenge and verify token.
    """
    if hub_mode == "subscribe" and hub_verify_token == settings.WHATSAPP_VERIFY_TOKEN:
        return Response(content=hub_challenge, media_type="text/plain")
    raise HTTPException(status_code=403, detail="Invalid verification token or mode.")

@router.post("/whatsapp")
async def receive_whatsapp_message(request: Request, db: Session = Depends(get_db)):
    """
    Direct WhatsApp Cloud API Webhook receiver.
    Parses incoming customer message, executes KiranaOS agent workflow with idempotency,
    and returns response.
    """
    body = await request.json()
    logger.info("Received WhatsApp Webhook: %s", body)

    # Standard WhatsApp Cloud API payload normalization
    message_text = ""
    from_number = "+919876543210"
    message_id = None

    try:
        entries = body.get("entry", [])
        if entries:
            changes = entries[0].get("changes", [])
            if changes:
                val = changes[0].get("value", {})
                messages = val.get("messages", [])
                if messages:
                    msg = messages[0]
                    message_id = msg.get("id")
                    from_number = f"+{msg.get('from')}" if not msg.get('from', '').startswith('+') else msg.get('from')
                    if msg.get("type") == "text":
                        message_text = msg.get("text", {}).get("body", "")
    except Exception as ex:
        logger.error("Error parsing WhatsApp payload: %s", ex)

    # Fallback to direct test payload format: {"from": "+91...", "message": "...", "message_id": "..."}
    if not message_text:
        message_text = body.get("message") or body.get("body", "")
        from_number = body.get("from") or body.get("from_number", from_number)
        message_id = body.get("message_id") or body.get("id")

    if not message_text:
        return {"status": "ignored", "reason": "No text message detected."}

    # Execute KiranaOS LangGraph Operator
    result = run_agent_workflow(
        message=message_text,
        phone=from_number,
        idempotency_key=message_id,
        request_id=f"wa_{message_id}" if message_id else None
    )

    return {
        "status": "processed",
        "agent_status": result["status"],
        "order_id": result.get("order_id"),
        "customer_message": message_text,
        "reply": result.get("confirmation_message")
    }

@router.post("/n8n")
async def receive_n8n_callback(request: Request):
    """Callback receiver for n8n automation executions."""
    data = await request.json()
    return {"status": "received", "payload": data}

@router.post("/delivery-mock")
async def mock_delivery_dispatch(request: Request):
    """Mock rider delivery partner dispatch endpoint."""
    data = await request.json()
    return {
        "status": "rider_assigned",
        "rider_name": "Ramesh Kumar (Kirana Express)",
        "rider_phone": "+919812345678",
        "eta": "18 mins",
        "order_id": data.get("order_id") or data.get("delivery_id")
    }
