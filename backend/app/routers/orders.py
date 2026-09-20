from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from backend.app.database import get_db
from backend.app.models import Order, OrderItem
from backend.app.schemas import OrderResponse

router = APIRouter(prefix="/orders", tags=["Orders"])

@router.get("", response_model=List[OrderResponse])
def list_orders(status: Optional[str] = None, limit: int = Query(30, ge=1, le=100), db: Session = Depends(get_db)):
    """List recent orders from the database."""
    query = db.query(Order)
    if status:
        query = query.filter(Order.status == status)
    orders = query.order_by(Order.created_at.desc()).limit(limit).all()
    return orders

@router.get("/pending-approvals", response_model=List[OrderResponse])
def list_pending_approvals(db: Session = Depends(get_db)):
    """List orders that require merchant human approval."""
    orders = db.query(Order).filter(Order.status == "pending_approval").order_by(Order.created_at.desc()).all()
    return orders

@router.get("/{order_id}", response_model=OrderResponse)
def get_single_order(order_id: str, db: Session = Depends(get_db)):
    """Retrieve details of a single committed order."""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail=f"Order '{order_id}' not found.")
    return order
