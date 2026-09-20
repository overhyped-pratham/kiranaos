import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from backend.app.database import get_db
from backend.app.schemas import ProductResponse, ProductUpdate, RestockRequest
from backend.app.models import Product, InventoryLog, LowStockEvent

router = APIRouter(prefix="/inventory", tags=["Inventory"])

@router.get("", response_model=List[ProductResponse])
def list_inventory(db: Session = Depends(get_db)):
    """Retrieve all active inventory items with live stock and pricing."""
    products = db.query(Product).order_by(Product.category, Product.name).all()
    return products

@router.get("/product/{product_id}", response_model=ProductResponse)
def get_single_product(product_id: str, db: Session = Depends(get_db)):
    """Retrieve single product details."""
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        raise HTTPException(status_code=404, detail=f"Product '{product_id}' not found.")
    return p

@router.patch("/product/{product_id}", response_model=ProductResponse)
def update_product_live(product_id: str, payload: ProductUpdate, db: Session = Depends(get_db)):
    """
    Live mutation endpoint for judges and merchants.
    Allows changing Maggi stock (e.g. 50 -> 0) or Atta price (e.g. 240 -> 260) on the fly!
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail=f"Product '{product_id}' not found.")

    if payload.price is not None:
        product.price = float(payload.price)

    if payload.stock is not None:
        if payload.stock < 0:
            raise HTTPException(status_code=400, detail="Stock cannot be negative.")
        prev_stock = product.stock
        product.stock = int(payload.stock)
        
        # Log inventory override
        log = InventoryLog(
            product_id=product.id,
            change_amount=product.stock - prev_stock,
            previous_stock=prev_stock,
            new_stock=product.stock,
            reason="judge_manual_override"
        )
        db.add(log)

    if payload.low_stock_threshold is not None:
        product.low_stock_threshold = int(payload.low_stock_threshold)

    if payload.active is not None:
        product.active = payload.active

    product.updated_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(product)
    return product

@router.post("/restock")
def restock_product(payload: RestockRequest, db: Session = Depends(get_db)):
    """Restock an existing product and log to inventory_logs."""
    product = db.query(Product).filter(Product.id == payload.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail=f"Product '{payload.product_id}' not found.")

    prev_stock = product.stock
    new_stock = prev_stock + payload.quantity
    product.stock = new_stock

    log = InventoryLog(
        product_id=product.id,
        change_amount=payload.quantity,
        previous_stock=prev_stock,
        new_stock=new_stock,
        reason=payload.reason or "manual_restock"
    )
    db.add(log)
    db.commit()

    return {
        "success": True,
        "product_id": product.id,
        "product_name": product.name,
        "previous_stock": prev_stock,
        "new_stock": new_stock,
        "restocked": payload.quantity
    }

@router.get("/low-stock-events")
def get_low_stock_events(limit: int = 20, db: Session = Depends(get_db)):
    """Retrieve history of triggered low-stock alerts."""
    events = db.query(LowStockEvent).order_by(LowStockEvent.triggered_at.desc()).limit(limit).all()
    return [
        {
            "id": e.id,
            "product_id": e.product_id,
            "product_name": e.product.name if e.product else "",
            "stock_at_event": e.stock_at_event,
            "threshold": e.threshold,
            "status": e.status,
            "triggered_at": e.triggered_at.isoformat() if e.triggered_at else None
        }
        for e in events
    ]

@router.get("/logs")
def get_inventory_logs(limit: int = 30, db: Session = Depends(get_db)):
    """Retrieve transactional audit logs of all inventory deductions and additions."""
    logs = db.query(InventoryLog).order_by(InventoryLog.timestamp.desc()).limit(limit).all()
    return [
        {
            "id": l.id,
            "product_id": l.product_id,
            "product_name": l.product.name if l.product else "",
            "order_id": l.order_id,
            "change_amount": l.change_amount,
            "previous_stock": l.previous_stock,
            "new_stock": l.new_stock,
            "reason": l.reason,
            "timestamp": l.timestamp.isoformat() if l.timestamp else None
        }
        for l in logs
    ]
