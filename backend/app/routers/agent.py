from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from backend.app.database import get_db
from backend.app.schemas import AgentRunRequest, AgentRunResponse, AgentApproveRequest
from backend.app.agent.graph import run_agent_workflow
from backend.app.models import AgentRun, Order
from backend.app.tools import store_tools
from backend.app.services.automation_service import automation_service

router = APIRouter(prefix="/agent", tags=["Agent"])

@router.post("/run", response_model=AgentRunResponse)
def execute_agent_run(payload: AgentRunRequest, db: Session = Depends(get_db)):
    """
    Main entrypoint for autonomous store operator.
    Receives customer natural-language query and runs stateful LangGraph operator.
    """
    state = run_agent_workflow(
        message=payload.message,
        phone=payload.phone or "+919876543210",
        customer_id=payload.customer_id,
        address=payload.address,
        idempotency_key=payload.idempotency_key,
        request_id=payload.request_id
    )

    return AgentRunResponse(
        run_id=state["run_id"],
        request_id=state["request_id"],
        customer_id=state.get("customer_id"),
        status=state["status"],
        message=state.get("confirmation_message") or "Request processed.",
        order=state.get("committed_order"),
        clarification_options=state.get("clarification_options"),
        low_stock_events=state.get("low_stock_events"),
        events=state.get("events", []),
        structured_intent=state.get("intent"),
        tool_calls=state.get("tool_calls")
    )

@router.post("/approve")
def approve_or_reject_order(payload: AgentApproveRequest, db: Session = Depends(get_db)):
    """
    Human-in-the-loop: Merchant approves or rejects an order held in pending_approval state.
    Resumes LangGraph transaction to deduct inventory, trigger delivery, and confirm.
    """
    order = db.query(Order).filter(Order.id == payload.order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail=f"Order '{payload.order_id}' not found.")

    if order.status != "pending_approval":
        return {
            "success": False,
            "message": f"Order is already in '{order.status}' status."
        }

    if payload.action.lower() == "approve":
        # 1. Update status
        order.status = "confirmed"
        db.commit()

        # 2. Transactionally update inventory
        inv_res = store_tools.update_inventory(db, order.id)
        if not inv_res["success"]:
            order.status = "failed"
            db.commit()
            return {
                "success": False,
                "error": f"Failed to deduct stock: {inv_res.get('error')}"
            }

        # 3. Create delivery
        del_res = store_tools.create_delivery(db, order.id, order.delivery_address)
        automation_service.trigger_delivery_dispatch(del_res)

        # 4. Check low stock
        if inv_res.get("low_stock_events"):
            automation_service.trigger_low_stock_alerts(inv_res["low_stock_events"])

        # 5. Send confirmation
        conf_res = store_tools.send_confirmation(db, order.id)
        msg = f"Merchant Approved! ✅\n{conf_res['confirmation_message']}"

        # 6. Notify customer via n8n
        automation_service.trigger_n8n_order_webhook({
            "order_id": order.id,
            "customer_id": order.customer_id,
            "message": msg,
            "total": order.total
        })

        return {
            "success": True,
            "status": "confirmed",
            "order_id": order.id,
            "total": order.total,
            "delivery": del_res,
            "message": msg
        }

    elif payload.action.lower() == "reject":
        order.status = "rejected"
        order.approval_reason = payload.reason or "Rejected by merchant."
        db.commit()

        return {
            "success": True,
            "status": "rejected",
            "order_id": order.id,
            "reason": order.approval_reason,
            "message": f"Order {order.id} was rejected by store operator."
        }

    else:
        raise HTTPException(status_code=400, detail="Action must be 'approve' or 'reject'.")

@router.get("/runs")
def get_agent_runs(limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    """Retrieve recent agent runs with complete event trace."""
    runs = db.query(AgentRun).order_by(AgentRun.created_at.desc()).limit(limit).all()
    return [
        {
            "run_id": r.id,
            "request_id": r.request_id,
            "customer_id": r.customer_id,
            "status": r.status,
            "input_text": r.input_text,
            "events_count": len(r.events or []),
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "final_message": (r.final_output or {}).get("message"),
            "order_id": (r.final_output or {}).get("order_id"),
            "events": r.events
        }
        for r in runs
    ]

@router.get("/runs/{run_id}")
def get_agent_run_detail(run_id: str, db: Session = Depends(get_db)):
    """Retrieve detailed trace for a specific agent run."""
    r = db.query(AgentRun).filter(AgentRun.id == run_id).first()
    if not r:
        raise HTTPException(status_code=404, detail=f"Agent run '{run_id}' not found.")
    return {
        "run_id": r.id,
        "request_id": r.request_id,
        "customer_id": r.customer_id,
        "status": r.status,
        "input_text": r.input_text,
        "structured_intent": r.structured_intent,
        "tool_calls": r.tool_calls,
        "events": r.events,
        "final_output": r.final_output,
        "created_at": r.created_at.isoformat() if r.created_at else None
    }
