import datetime
import threading
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc
from backend.app.models import (
    Product,
    Customer,
    Order,
    OrderItem,
    InventoryLog,
    AgentRun,
    CustomerPreference,
    LowStockEvent,
    DeliveryRequest
)
from backend.app.config import settings

# Threading lock for serialized transactional inventory mutations (concurrency safety)
_inventory_lock = threading.Lock()

def search_products(db: Session, query: str, top_k: int = 5) -> Dict[str, Any]:
    """Search products in database by exact text, brand, category, or alias."""
    q = query.strip().lower()
    if not q:
        products = db.query(Product).filter(Product.active == True).limit(top_k).all()
        return {
            "success": True,
            "query": query,
            "count": len(products),
            "products": [
                {
                    "id": p.id,
                    "name": p.name,
                    "brand": p.brand,
                    "size": p.size,
                    "price": p.price,
                    "stock": p.stock,
                    "unit": p.unit,
                    "low_stock_threshold": p.low_stock_threshold,
                    "aliases": p.aliases
                }
                for p in products
            ]
        }

    # Query DB with filter
    all_active = db.query(Product).filter(Product.active == True).all()
    matched = []
    
    for p in all_active:
        score = 0
        name_lower = p.name.lower()
        brand_lower = p.brand.lower()
        category_lower = p.category.lower()
        aliases_lower = [a.lower() for a in p.aliases]

        if q in name_lower:
            score += 10
        if q in brand_lower:
            score += 8
        if q in category_lower:
            score += 5
        for alias in aliases_lower:
            if q in alias or alias in q:
                score += 7
        
        # Word overlap
        q_words = set(q.split())
        prod_words = set((name_lower + " " + brand_lower + " " + " ".join(aliases_lower)).split())
        common = q_words.intersection(prod_words)
        score += len(common) * 3

        if score > 0:
            matched.append((score, p))

    matched.sort(key=lambda x: x[0], reverse=True)
    results = [
        {
            "id": p.id,
            "name": p.name,
            "brand": p.brand,
            "size": p.size,
            "price": p.price,
            "stock": p.stock,
            "unit": p.unit,
            "low_stock_threshold": p.low_stock_threshold,
            "score": score
        }
        for score, p in matched[:top_k]
    ]

    return {
        "success": True,
        "query": query,
        "count": len(results),
        "products": results
    }


def get_product(db: Session, product_id: str) -> Dict[str, Any]:
    """Retrieve full product details from database."""
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        return {"success": False, "error": f"Product '{product_id}' not found."}
    return {
        "success": True,
        "product": {
            "id": p.id,
            "name": p.name,
            "brand": p.brand,
            "category": p.category,
            "size": p.size,
            "unit": p.unit,
            "price": p.price,
            "stock": p.stock,
            "low_stock_threshold": p.low_stock_threshold,
            "aliases": p.aliases,
            "active": p.active
        }
    }


def check_inventory(db: Session, product_id: str, requested_quantity: int) -> Dict[str, Any]:
    """Check live stock in database. Invariant: never fabricate stock numbers."""
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        return {
            "success": False,
            "product_id": product_id,
            "error": "Product does not exist in inventory"
        }
    
    is_available = p.stock >= requested_quantity
    return {
        "success": True,
        "product_id": p.id,
        "product_name": p.name,
        "stock": p.stock,
        "requested": requested_quantity,
        "available": is_available,
        "shortage": max(0, requested_quantity - p.stock),
        "is_low_stock": p.stock <= p.low_stock_threshold
    }


def get_price(db: Session, product_id: str) -> Dict[str, Any]:
    """Fetch authoritative price directly from database."""
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        return {"success": False, "error": f"Product '{product_id}' not found."}
    return {
        "success": True,
        "product_id": p.id,
        "name": p.name,
        "price": p.price
    }


def get_customer(db: Session, customer_id_or_phone: str) -> Dict[str, Any]:
    """Retrieve customer profile by ID or phone number."""
    c = db.query(Customer).filter(
        or_(Customer.id == customer_id_or_phone, Customer.phone == customer_id_or_phone)
    ).first()
    if not c:
        return {"success": False, "error": "Customer not found."}
    return {
        "success": True,
        "customer": {
            "id": c.id,
            "phone": c.phone,
            "name": c.name,
            "default_address": c.default_address,
            "preferences": c.preferences
        }
    }


def get_customer_history(db: Session, customer_id: str) -> Dict[str, Any]:
    """Retrieve customer's previous orders and frequent items for memory feature."""
    orders = db.query(Order).filter(Order.customer_id == customer_id).order_by(desc(Order.created_at)).limit(5).all()
    prefs = db.query(CustomerPreference).filter(CustomerPreference.customer_id == customer_id).order_by(desc(CustomerPreference.frequency)).all()

    past_orders = []
    for ord in orders:
        items = [
            {
                "product_id": item.product_id,
                "product_name": item.product_name,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "line_total": item.line_total
            }
            for item in ord.items
        ]
        past_orders.append({
            "order_id": ord.id,
            "status": ord.status,
            "total": ord.total,
            "created_at": ord.created_at.isoformat() if ord.created_at else None,
            "items": items
        })

    frequent_items = [
        {
            "product_id": pref.product_id,
            "product_name": pref.product.name if pref.product else "",
            "frequency": pref.frequency,
            "preferred_quantity": pref.preferred_quantity,
            "price": pref.product.price if pref.product else 0.0
        }
        for pref in prefs
    ]

    return {
        "success": True,
        "customer_id": customer_id,
        "past_orders": past_orders,
        "frequent_items": frequent_items,
        "last_order": past_orders[0] if past_orders else None
    }


def calculate_order(db: Session, items: List[Dict[str, Any]], delivery_required: bool = True) -> Dict[str, Any]:
    """Calculate order totals authoritatively from live DB prices. Never let LLM calculate total."""
    subtotal = 0.0
    line_items = []

    for item in items:
        p_id = item["product_id"]
        qty = int(item["quantity"])
        p = db.query(Product).filter(Product.id == p_id).first()
        if not p:
            return {"success": False, "error": f"Product '{p_id}' not found in database."}
        
        unit_price = float(p.price)
        line_total = round(unit_price * qty, 2)
        subtotal = round(subtotal + line_total, 2)

        line_items.append({
            "product_id": p.id,
            "product_name": p.name,
            "quantity": qty,
            "unit_price": unit_price,
            "line_total": line_total
        })

    delivery_charge = 0.0
    if delivery_required:
        if subtotal >= settings.FREE_DELIVERY_THRESHOLD:
            delivery_charge = 0.0
        else:
            delivery_charge = settings.DEFAULT_DELIVERY_CHARGE

    total = round(subtotal + delivery_charge, 2)

    return {
        "success": True,
        "items": line_items,
        "subtotal": subtotal,
        "delivery_charge": delivery_charge,
        "total": total,
        "free_delivery": delivery_charge == 0.0 and delivery_required
    }


def create_order(
    db: Session,
    customer_id: str,
    calculated_order: Dict[str, Any],
    idempotency_key: Optional[str] = None,
    delivery_address: Optional[str] = None,
    status: str = "confirmed",
    approval_reason: Optional[str] = None
) -> Dict[str, Any]:
    """Create order in database. Strictly checks idempotency to prevent duplicate orders."""
    # 1. Check idempotency
    if idempotency_key:
        existing = db.query(Order).filter(Order.idempotency_key == idempotency_key).first()
        if existing:
            return {
                "success": True,
                "duplicate": True,
                "message": "Order already processed with this idempotency key.",
                "order_id": existing.id,
                "order": {
                    "id": existing.id,
                    "customer_id": existing.customer_id,
                    "status": existing.status,
                    "subtotal": existing.subtotal,
                    "delivery_charge": existing.delivery_charge,
                    "total": existing.total,
                    "delivery_status": existing.delivery_status,
                    "delivery_address": existing.delivery_address,
                    "created_at": existing.created_at.isoformat() if existing.created_at else None,
                    "items": [
                        {
                            "product_id": i.product_id,
                            "product_name": i.product_name,
                            "quantity": i.quantity,
                            "unit_price": i.unit_price,
                            "line_total": i.line_total
                        }
                        for i in existing.items
                    ]
                }
            }

    # 2. Collision-free sequential Order ID generation with atomic retry loop
    today_str = datetime.datetime.utcnow().strftime("%Y%m%d")
    max_retries = 6
    new_order = None
    order_id = None

    for attempt in range(max_retries):
        try:
            # Query existing orders for today to find highest sequence
            existing_orders = db.query(Order.id).filter(Order.id.like(f"ORD-{today_str}-%")).all()
            max_seq = 0
            for (ord_id_str,) in existing_orders:
                parts = ord_id_str.split("-")
                if len(parts) >= 3 and parts[2][:4].isdigit():
                    max_seq = max(max_seq, int(parts[2][:4]))

            next_seq = max_seq + 1 + attempt
            candidate_id = f"ORD-{today_str}-{next_seq:04d}"

            # If attempt > 1, add random entropy to eliminate race conditions
            if attempt > 1:
                import uuid
                candidate_id = f"ORD-{today_str}-{next_seq:04d}-{uuid.uuid4().hex[:4].upper()}"

            # Check if this ID already exists
            if db.query(Order.id).filter(Order.id == candidate_id).first():
                continue

            # PostgreSQL Foreign Key Invariant: Ensure customer exists in database
            cust = db.query(Customer).filter(Customer.id == customer_id).first()
            if not cust:
                import uuid
                cust_phone = customer_id if customer_id.startswith("+") else f"+9198{abs(hash(customer_id)) % 100000000:08d}"
                if db.query(Customer).filter(Customer.phone == cust_phone).first():
                    cust_phone = f"+91{uuid.uuid4().int % 10000000000:010d}"
                cust = Customer(
                    id=customer_id,
                    phone=cust_phone,
                    name="Walk-in Customer",
                    default_address=delivery_address or "Local Delivery",
                    preferences={}
                )
                db.add(cust)
                db.flush()

            order_id = candidate_id
            new_order = Order(
                id=order_id,
                customer_id=customer_id,
                status=status,
                subtotal=calculated_order["subtotal"],
                delivery_charge=calculated_order["delivery_charge"],
                total=calculated_order["total"],
                idempotency_key=idempotency_key,
                delivery_status="requested" if status == "confirmed" else "pending",
                delivery_address=delivery_address,
                approval_reason=approval_reason
            )
            db.add(new_order)
            db.flush()

            # Create OrderItems
            for item in calculated_order["items"]:
                order_item = OrderItem(
                    order_id=order_id,
                    product_id=item["product_id"],
                    product_name=item["product_name"],
                    quantity=item["quantity"],
                    unit_price=item["unit_price"],
                    line_total=item["line_total"]
                )
                db.add(order_item)

            db.commit()
            db.refresh(new_order)
            break
        except Exception:
            db.rollback()
            if attempt == max_retries - 1:
                # Final fallback guarantee: microsecond timestamp + UUID entropy
                import uuid
                micro_ts = datetime.datetime.utcnow().strftime("%f")[:3]
                order_id = f"ORD-{today_str}-{max_seq + 1:04d}-{micro_ts}{uuid.uuid4().hex[:3].upper()}"
                new_order = Order(
                    id=order_id,
                    customer_id=customer_id,
                    status=status,
                    subtotal=calculated_order["subtotal"],
                    delivery_charge=calculated_order["delivery_charge"],
                    total=calculated_order["total"],
                    idempotency_key=idempotency_key,
                    delivery_status="requested" if status == "confirmed" else "pending",
                    delivery_address=delivery_address,
                    approval_reason=approval_reason
                )
                db.add(new_order)
                for item in calculated_order["items"]:
                    order_item = OrderItem(
                        order_id=order_id,
                        product_id=item["product_id"],
                        product_name=item["product_name"],
                        quantity=item["quantity"],
                        unit_price=item["unit_price"],
                        line_total=item["line_total"]
                    )
                    db.add(order_item)
                db.commit()
                db.refresh(new_order)
                break

    return {
        "success": True,
        "duplicate": False,
        "order_id": order_id,
        "order": {
            "id": new_order.id,
            "customer_id": new_order.customer_id,
            "status": new_order.status,
            "subtotal": new_order.subtotal,
            "delivery_charge": new_order.delivery_charge,
            "total": new_order.total,
            "delivery_status": new_order.delivery_status,
            "delivery_address": new_order.delivery_address,
            "approval_reason": new_order.approval_reason,
            "created_at": new_order.created_at.isoformat() if new_order.created_at else None,
            "items": calculated_order["items"]
        }
    }


def update_inventory(db: Session, order_id: str) -> Dict[str, Any]:
    """Transactional inventory deduction. Enforces stock >= 0. Emits low-stock alert if threshold reached."""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        return {"success": False, "error": f"Order '{order_id}' not found."}

    with _inventory_lock:
        # Verify all items have sufficient stock first (atomic check)
        for item in order.items:
            product = db.query(Product).filter(Product.id == item.product_id).with_for_update().first()
            if not product:
                order.status = "failed"
                order.approval_reason = f"Product '{item.product_id}' no longer exists."
                db.commit()
                return {"success": False, "error": order.approval_reason}
            if product.stock < item.quantity:
                # Mark order as failed in database immediately
                order.status = "failed"
                order.approval_reason = f"Insufficient stock for '{product.name}'. Available: {product.stock}, Requested: {item.quantity}."
                db.commit()
                return {
                    "success": False,
                    "error": order.approval_reason
                }

        deductions = []
        low_stock_events = []

        # Perform mutations
        for item in order.items:
            product = db.query(Product).filter(Product.id == item.product_id).first()
            prev_stock = product.stock
            new_stock = prev_stock - item.quantity

            product.stock = new_stock
            
            # Log to inventory_logs
            log_entry = InventoryLog(
                product_id=product.id,
                order_id=order.id,
                change_amount=-item.quantity,
                previous_stock=prev_stock,
                new_stock=new_stock,
                reason="order_fulfillment"
            )
            db.add(log_entry)

            deductions.append({
                "product_id": product.id,
                "product_name": product.name,
                "previous_stock": prev_stock,
                "new_stock": new_stock,
                "deducted": item.quantity
            })

            # Check low stock threshold
            if new_stock <= product.low_stock_threshold:
                event = create_low_stock_alert(db, product.id)
                low_stock_events.append(event)

        db.commit()

        return {
            "success": True,
            "order_id": order_id,
            "deductions": deductions,
            "low_stock_events": low_stock_events
        }


def create_delivery(db: Session, order_id: str, address: Optional[str] = None) -> Dict[str, Any]:
    """Create delivery request for confirmed order. Idempotent if called multiple times."""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        return {"success": False, "error": f"Order '{order_id}' not found."}

    delivery_addr = address or order.delivery_address or "Customer Default Address"
    del_id = f"DEL-{order.id.replace('ORD-', '')}"
    tracking_id = f"TRK-{order.id.replace('ORD-', '')}-EXP"

    # Idempotent return if delivery request already exists
    existing = db.query(DeliveryRequest).filter(DeliveryRequest.id == del_id).first()
    if existing:
        if address:
            existing.address = address
            order.delivery_address = address
            db.commit()
        return {
            "success": True,
            "delivery_id": existing.id,
            "tracking_id": existing.tracking_id,
            "address": existing.address,
            "estimated_time": existing.estimated_time,
            "status": existing.status
        }

    delivery = DeliveryRequest(
        id=del_id,
        order_id=order.id,
        address=delivery_addr,
        status="assigned",
        delivery_partner="Kirana Express Rider",
        estimated_time="15-25 mins",
        tracking_id=tracking_id
    )
    db.add(delivery)
    order.delivery_status = "dispatched"
    order.delivery_address = delivery_addr
    db.commit()

    return {
        "success": True,
        "delivery_id": del_id,
        "tracking_id": tracking_id,
        "address": delivery_addr,
        "estimated_time": "15-25 mins",
        "status": "assigned"
    }



def update_delivery_status(db: Session, delivery_id: str, new_status: str) -> Dict[str, Any]:
    """
    Update delivery status through its lifecycle: assigned -> out_for_delivery -> delivered -> failed.
    Synchronizes delivery_status on the corresponding Order model.
    """
    del_req = db.query(DeliveryRequest).filter(DeliveryRequest.id == delivery_id).first()
    if not del_req:
        return {"success": False, "error": f"Delivery '{delivery_id}' not found."}

    del_req.status = new_status
    order = db.query(Order).filter(Order.id == del_req.order_id).first()
    if order:
        order.delivery_status = new_status
    db.commit()
    return {
        "success": True,
        "delivery_id": delivery_id,
        "status": new_status,
        "order_id": del_req.order_id
    }


def send_confirmation(db: Session, order_id: str) -> Dict[str, Any]:
    """Authoritative order confirmation generated directly from committed database record."""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        return {"success": False, "error": f"Order '{order_id}' does not exist."}

    lines = [f"Order confirmed! 🛒\n", f"Order: *{order.id}*\n"]
    for item in order.items:
        lines.append(f"• {item.quantity} × {item.product_name} (₹{item.unit_price}) = ₹{item.line_total}")

    lines.append(f"\nSubtotal: ₹{order.subtotal}")
    if order.delivery_charge > 0:
        lines.append(f"Delivery: ₹{order.delivery_charge}")
    else:
        lines.append(f"Delivery: FREE (Above ₹{settings.FREE_DELIVERY_THRESHOLD})")
    lines.append(f"*Total: ₹{order.total}*")

    if order.delivery_address:
        lines.append(f"\n📍 Delivering to: {order.delivery_address}")
    lines.append("⚡ Estimated Delivery: 15-25 mins. We'll notify you when it's dispatched!")

    message = "\n".join(lines)
    return {
        "success": True,
        "order_id": order.id,
        "total": order.total,
        "confirmation_message": message
    }


def create_low_stock_alert(db: Session, product_id: str) -> Dict[str, Any]:
    """Trigger low-stock alert when inventory drops to or below threshold."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        return {"success": False, "error": "Product not found"}

    # Avoid spamming duplicate alerts if one was created recently today
    today = datetime.datetime.utcnow().date()
    existing = db.query(LowStockEvent).filter(
        LowStockEvent.product_id == product_id,
        LowStockEvent.triggered_at >= datetime.datetime(today.year, today.month, today.day)
    ).first()

    if existing:
        return {
            "success": True,
            "product_id": product_id,
            "product_name": product.name,
            "stock": product.stock,
            "threshold": product.low_stock_threshold,
            "alert_status": "already_alerted_today"
        }

    event = LowStockEvent(
        product_id=product_id,
        stock_at_event=product.stock,
        threshold=product.low_stock_threshold,
        status="alert_triggered"
    )
    db.add(event)
    db.commit()

    return {
        "success": True,
        "product_id": product_id,
        "product_name": product.name,
        "stock": product.stock,
        "threshold": product.low_stock_threshold,
        "alert_status": "alert_triggered"
    }


def save_customer_preference(db: Session, customer_id: str, items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Save customer preferences and order frequency for customer memory feature."""
    for item in items:
        p_id = item["product_id"]
        qty = item["quantity"]
        pref = db.query(CustomerPreference).filter(
            CustomerPreference.customer_id == customer_id,
            CustomerPreference.product_id == p_id
        ).first()

        if pref:
            pref.frequency += 1
            pref.preferred_quantity = qty
            pref.last_ordered_at = datetime.datetime.utcnow()
        else:
            new_pref = CustomerPreference(
                customer_id=customer_id,
                product_id=p_id,
                frequency=1,
                preferred_quantity=qty,
                last_ordered_at=datetime.datetime.utcnow()
            )
            db.add(new_pref)

    db.commit()
    return {"success": True, "customer_id": customer_id}


def log_agent_event(db: Session, run_id: str, event_type: str, details: Dict[str, Any], tool: Optional[str] = None):
    """Log an observable backend event to AgentRun. Never fake events."""
    agent_run = db.query(AgentRun).filter(AgentRun.id == run_id).first()
    if agent_run:
        events = list(agent_run.events or [])
        events.append({
            "timestamp": datetime.datetime.utcnow().strftime("%H:%M:%S.%f")[:-3],
            "event": event_type,
            "tool": tool,
            "details": details
        })
        agent_run.events = events
        db.commit()
