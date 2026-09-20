import datetime
import uuid
from typing import Dict, Any, List, Optional
from langgraph.graph import StateGraph, END
from sqlalchemy.orm import Session

from backend.app.agent.state import AgentState
from backend.app.database import SessionLocal
from backend.app.tools import store_tools
from backend.app.services.llm_service import llm_service
from backend.app.services.semantic_search import semantic_search
from backend.app.services.memory_service import memory_service
from backend.app.services.automation_service import automation_service
from backend.app.models import AgentRun
from backend.app.config import settings

def append_event(state: AgentState, event_name: str, details: Dict[str, Any], tool: Optional[str] = None):
    now_str = datetime.datetime.utcnow().strftime("%H:%M:%S.%f")[:-3]
    state["events"].append({
        "timestamp": now_str,
        "event": event_name,
        "tool": tool,
        "details": details
    })

# Node 1: Parse Request & Identify Customer
def parse_request_node(state: AgentState) -> AgentState:
    db: Session = SessionLocal()
    try:
        append_event(state, "REQUEST_RECEIVED", {"input_text": state["input_text"], "request_id": state["request_id"]})

        # 1. Customer resolution
        cust_res = store_tools.get_customer(db, state["customer_phone"])
        if cust_res["success"]:
            cust = cust_res["customer"]
            state["customer_id"] = cust["id"]
            state["customer_name"] = cust["name"]
            if not state["delivery_address"]:
                state["delivery_address"] = cust["default_address"]
        else:
            cust_id = f"cust_{state['customer_phone'].replace('+', '')}"
            from backend.app.models import Customer
            existing_cust = db.query(Customer).filter(Customer.id == cust_id).first()
            if not existing_cust:
                new_cust = Customer(
                    id=cust_id,
                    phone=state["customer_phone"],
                    name="Walk-in Customer",
                    default_address=state.get("delivery_address") or "Local Delivery",
                    preferences={}
                )
                db.add(new_cust)
                try:
                    db.commit()
                except Exception:
                    db.rollback()
            state["customer_id"] = cust_id
            state["customer_name"] = "Walk-in Customer"

        # 2. Idempotency Check
        if state["idempotency_key"]:
            append_event(state, "IDEMPOTENCY_CHECK", {"idempotency_key": state["idempotency_key"]}, tool="check_idempotency")
            existing_ord = store_tools.create_order(
                db,
                customer_id=state["customer_id"],
                calculated_order={"subtotal": 0, "delivery_charge": 0, "total": 0, "items": []},
                idempotency_key=state["idempotency_key"]
            )
            if existing_ord.get("duplicate"):
                state["is_duplicate"] = True
                state["order_id"] = existing_ord["order_id"]
                state["committed_order"] = existing_ord["order"]
                state["status"] = "duplicate_ignored"
                conf = store_tools.send_confirmation(db, existing_ord["order_id"])
                state["confirmation_message"] = (
                    f"⚠️ Duplicate request detected (Idempotency Key: {state['idempotency_key']}).\n"
                    f"Returning previously confirmed order:\n\n{conf.get('confirmation_message')}"
                )
                append_event(state, "DUPLICATE_REQUEST_IGNORED", {"existing_order_id": existing_ord["order_id"]})
                return state

        # 3. LLM Intent & Structured Extraction
        intent_res = llm_service.parse_customer_intent(state["input_text"])
        state["intent"] = intent_res
        state["extracted_items"] = intent_res.get("items", [])
        append_event(state, "INTENT_PARSED", {"intent": intent_res.get("intent"), "item_count": len(state["extracted_items"])}, tool="qwen_parse_intent")

        return state
    finally:
        db.close()

# Node 2: Extract & Expand Items (handles "usual samaan" memory)
def extract_items_node(state: AgentState) -> AgentState:
    if state["is_duplicate"]:
        return state

    db: Session = SessionLocal()
    try:
        intent = state["intent"].get("intent")
        if intent == "repeat_usual" or not state["extracted_items"]:
            # Retrieve customer memory
            append_event(state, "MEMORY_RETRIEVAL", {"customer_id": state["customer_id"]}, tool="get_customer_history")
            usual_res = memory_service.reconstruct_usual_order(db, state["customer_id"])
            if usual_res["success"]:
                state["extracted_items"] = usual_res["items"]
                append_event(state, "USUAL_ORDER_RECONSTRUCTED", {"items": usual_res["items"], "source": usual_res["source"]})
            else:
                state["status"] = "needs_clarification"
                state["confirmation_message"] = "Aapka koi purana order record nahi mila. Kripya samaan ki list bataiye."
                append_event(state, "MEMORY_EMPTY", {"reason": "no_previous_orders"})
                return state

        append_event(state, "ITEMS_EXTRACTED", {"items": state["extracted_items"]})
        return state
    finally:
        db.close()

# Node 3: Semantic Product Retrieval & Reranker
def resolve_products_node(state: AgentState) -> AgentState:
    if state["is_duplicate"] or state["status"] in ["needs_clarification", "failed"]:
        return state

    db: Session = SessionLocal()
    try:
        state["resolved_items"] = []
        state["unresolved_items"] = []

        for item in state["extracted_items"]:
            q = item["product_query"]
            qty = item.get("quantity", 1)
            size_hint = item.get("size_hint")

            append_event(state, "PRODUCT_SEARCH", {"query": q, "size_hint": size_hint}, tool="search_products")
            state["tool_calls"].append({"tool": "search_products", "query": q, "size_hint": size_hint})

            # BGE-M3 candidate retrieval + reranker
            resolution = semantic_search.rerank_and_resolve(db, query=q, size_hint=size_hint)

            if resolution["resolved"]:
                prod = resolution["product"]
                state["resolved_items"].append({
                    "product_id": prod["id"],
                    "product_name": prod["name"],
                    "quantity": qty,
                    "unit_price": prod["price"],
                    "brand": prod["brand"],
                    "size": prod["size"],
                    "confidence": resolution["confidence"]
                })
                append_event(state, "PRODUCT_RESOLVED", {
                    "query": q,
                    "product_id": prod["id"],
                    "product_name": prod["name"],
                    "confidence": resolution["confidence"]
                }, tool="resolve_product")
            else:
                state["unresolved_items"].append({
                    "query": q,
                    "quantity": qty,
                    "reason": resolution["reason"],
                    "alternatives": resolution.get("alternatives", []),
                    "candidates": resolution.get("candidates", []),
                    "message": resolution.get("message", "")
                })
                append_event(state, "PRODUCT_UNRESOLVED", {
                    "query": q,
                    "reason": resolution["reason"],
                    "options_count": len(resolution.get("alternatives", []) or resolution.get("candidates", []))
                })

        return state
    finally:
        db.close()

# Node 4: Live Inventory & Pricing Lookup
def lookup_inventory_pricing_node(state: AgentState) -> AgentState:
    if state["is_duplicate"] or state["status"] in ["needs_clarification", "failed"]:
        return state

    db: Session = SessionLocal()
    try:
        state["inventory_status"] = []

        for item in state["resolved_items"]:
            p_id = item["product_id"]
            qty = item["quantity"]

            # Live check inventory
            inv = store_tools.check_inventory(db, p_id, qty)
            price_res = store_tools.get_price(db, p_id)

            append_event(state, "INVENTORY_CHECK", {
                "product_id": p_id,
                "requested": qty,
                "stock": inv["stock"],
                "available": inv["available"]
            }, tool="check_inventory")
            state["tool_calls"].append({"tool": "check_inventory", "product_id": p_id, "requested": qty})

            append_event(state, "PRICE_RETRIEVED", {
                "product_id": p_id,
                "authoritative_price": price_res.get("price")
            }, tool="get_price")
            state["tool_calls"].append({"tool": "get_price", "product_id": p_id})

            state["inventory_status"].append(inv)
            # Update unit price from authoritative live DB price
            item["unit_price"] = price_res.get("price", item["unit_price"])

        return state
    finally:
        db.close()

# Node 5: Validate Availability & Human Approval check
def validate_availability_node(state: AgentState) -> AgentState:
    if state["is_duplicate"] or state["status"] in ["needs_clarification", "failed"]:
        return state

    db: Session = SessionLocal()
    try:
        # 1. If any item was unresolved (unavailable product or ambiguous size)
        if state["unresolved_items"]:
            state["status"] = "needs_clarification"
            clarifications = []
            msg_lines = []

            for unres in state["unresolved_items"]:
                q = unres["query"]
                if unres["reason"] == "ambiguous_size":
                    msg_lines.append(f"Multiple sizes are available for '{q}':")
                    for c in unres.get("candidates", []):
                        msg_lines.append(f"• {c['name']} ({c['size']}) — ₹{c['price']} (Stock: {c['stock']})")
                        clarifications.append({"action": "select_product", "product_id": c["product_id"], "label": f"{c['name']} - ₹{c['price']}"})
                else:
                    msg_lines.append(f"We could not find exact product for '{q}'. Available alternatives:")
                    for alt in unres.get("alternatives", []):
                        msg_lines.append(f"• {alt['name']} ({alt['size']}) — ₹{alt['price']} (Stock: {alt['stock']})")
                        clarifications.append({"action": "select_product", "product_id": alt["product_id"], "label": f"{alt['name']} - ₹{alt['price']}"})

            msg_lines.append("Which one would you like?")
            state["confirmation_message"] = "\n".join(msg_lines)
            state["clarification_options"] = clarifications
            append_event(state, "CLARIFICATION_REQUIRED", {"reason": "unresolved_or_ambiguous_products"})
            return state

        # 2. Check for Insufficient Stock
        insufficient_items = [inv for inv in state["inventory_status"] if not inv["available"]]
        if insufficient_items:
            state["status"] = "needs_clarification"
            msg_lines = []
            options = []

            for inv in insufficient_items:
                p_name = inv["product_name"]
                stock = inv["stock"]
                req = inv["requested"]

                if stock == 0:
                    msg_lines.append(f"'{p_name}' is currently out of stock (Stock: 0).")
                    # Search alternatives in same category
                    prod = db.query(store_tools.Product).filter(store_tools.Product.id == inv["product_id"]).first()
                    if prod:
                        alts = db.query(store_tools.Product).filter(
                            store_tools.Product.category == prod.category,
                            store_tools.Product.id != prod.id,
                            store_tools.Product.stock > 0
                        ).limit(2).all()
                        if alts:
                            msg_lines.append("Available alternatives:")
                            for a in alts:
                                msg_lines.append(f"• {a.name} — ₹{a.price} (Stock: {a.stock})")
                                options.append({"action": "substitute", "product_id": a.id, "label": f"Send {a.name}"})
                else:
                    msg_lines.append(f"I only have {stock} {p_name} available (requested: {req}).")
                    options.append({"action": "partial_fulfill", "product_id": inv["product_id"], "quantity": stock, "label": f"Send {stock} available"})
                    options.append({"action": "cancel", "label": "Cancel this item"})

            msg_lines.append("Would you like me to send the available quantity or choose an alternative?")
            state["confirmation_message"] = "\n".join(msg_lines)
            state["clarification_options"] = options
            append_event(state, "INSUFFICIENT_STOCK_DETECTED", {"shortages": insufficient_items})
            return state

        # 3. Check for Human Approval (Large orders, bulk quantity)
        total_items_qty = sum(item["quantity"] for item in state["resolved_items"])
        bulk_items = [item for item in state["resolved_items"] if item["quantity"] >= settings.HIGH_QUANTITY_APPROVAL_THRESHOLD]

        if bulk_items or total_items_qty >= 25:
            state["approval_needed"] = True
            bulk_names = [f"{i['product_name']} ({i['quantity']} units)" for i in bulk_items]
            reason = f"Bulk quantity request: {', '.join(bulk_names)}."
            state["approval_reason"] = reason
            state["status"] = "pending_approval"
            append_event(state, "HUMAN_APPROVAL_TRIGGERED", {"reason": reason, "threshold": settings.HIGH_QUANTITY_APPROVAL_THRESHOLD})

        return state
    finally:
        db.close()

# Node 6: Calculate Order Authoritatively
def calculate_order_node(state: AgentState) -> AgentState:
    if state["is_duplicate"] or state["status"] == "needs_clarification":
        return state

    db: Session = SessionLocal()
    try:
        # Authoritative calculation strictly using DB prices
        calc = store_tools.calculate_order(
            db,
            items=[{"product_id": i["product_id"], "quantity": i["quantity"]} for i in state["resolved_items"]],
            delivery_required=state["intent"].get("delivery_required", True)
        )
        state["calculated_order"] = calc
        state["tool_calls"].append({"tool": "calculate_order", "items_count": len(state["resolved_items"])})
        append_event(state, "ORDER_CALCULATED", {
            "subtotal": calc["subtotal"],
            "delivery_charge": calc["delivery_charge"],
            "total": calc["total"]
        }, tool="calculate_order")

        # Check total value approval
        if calc["total"] >= settings.HIGH_VALUE_APPROVAL_THRESHOLD and not state["approval_needed"]:
            state["approval_needed"] = True
            state["approval_reason"] = f"High value order (₹{calc['total']} exceeds ₹{settings.HIGH_VALUE_APPROVAL_THRESHOLD} threshold)."
            state["status"] = "pending_approval"
            append_event(state, "HUMAN_APPROVAL_TRIGGERED", {"reason": state["approval_reason"]})

        return state
    finally:
        db.close()

# Node 7: Create Order (Database Transaction)
def create_order_node(state: AgentState) -> AgentState:
    if state["is_duplicate"] or state["status"] == "needs_clarification":
        return state

    db: Session = SessionLocal()
    try:
        order_status = "pending_approval" if state["approval_needed"] else "confirmed"
        
        ord_res = store_tools.create_order(
            db,
            customer_id=state["customer_id"],
            calculated_order=state["calculated_order"],
            idempotency_key=state["idempotency_key"],
            delivery_address=state["delivery_address"],
            status=order_status,
            approval_reason=state.get("approval_reason")
        )
        state["order_id"] = ord_res["order_id"]
        state["committed_order"] = ord_res["order"]
        state["tool_calls"].append({"tool": "create_order", "order_id": ord_res["order_id"]})
        append_event(state, "ORDER_CREATED", {
            "order_id": ord_res["order_id"],
            "status": order_status,
            "total": ord_res["order"]["total"]
        }, tool="create_order")

        if state["approval_needed"]:
            state["status"] = "pending_approval"
            state["confirmation_message"] = (
                f"Your order {ord_res['order_id']} (Total: ₹{ord_res['order']['total']}) requires merchant confirmation "
                f"due to: {state['approval_reason']}. We have notified the store merchant for approval."
            )
            return state

        return state
    finally:
        db.close()

# Node 8: Update Inventory Transactionally
def update_inventory_node(state: AgentState) -> AgentState:
    if state["is_duplicate"] or state["status"] in ["needs_clarification", "pending_approval", "failed"]:
        return state

    db: Session = SessionLocal()
    try:
        inv_res = store_tools.update_inventory(db, state["order_id"])
        if not inv_res["success"]:
            state["status"] = "failed"
            state["confirmation_message"] = f"Failed to commit inventory: {inv_res.get('error')}"
            append_event(state, "INVENTORY_UPDATE_FAILED", {"error": inv_res.get("error")})
            return state

        state["low_stock_events"] = inv_res.get("low_stock_events", [])
        state["tool_calls"].append({"tool": "update_inventory", "order_id": state["order_id"]})
        append_event(state, "INVENTORY_UPDATED", {
            "order_id": state["order_id"],
            "deductions": inv_res.get("deductions", []),
            "low_stock_alerts_count": len(state["low_stock_events"])
        }, tool="update_inventory")

        # Save customer preferences for future memory
        store_tools.save_customer_preference(
            db,
            customer_id=state["customer_id"],
            items=[{"product_id": i["product_id"], "quantity": i["quantity"]} for i in state["resolved_items"]]
        )

        return state
    finally:
        db.close()

# Node 9: Post-Order Automations (Delivery, Low-Stock Alert, n8n)
def post_order_automations_node(state: AgentState) -> AgentState:
    if state["is_duplicate"] or state["status"] in ["needs_clarification", "pending_approval", "failed"]:
        return state

    db: Session = SessionLocal()
    try:
        # 1. Create delivery request
        del_res = store_tools.create_delivery(db, state["order_id"], state["delivery_address"])
        state["delivery_info"] = del_res
        state["tool_calls"].append({"tool": "create_delivery", "delivery_id": del_res.get("delivery_id")})
        append_event(state, "DELIVERY_CREATED", del_res, tool="create_delivery")

        # 2. Trigger downstream automations (n8n WhatsApp + Delivery partner)
        automation_service.trigger_delivery_dispatch(del_res)

        # 3. Trigger low-stock alert via n8n if any item crossed threshold
        if state["low_stock_events"]:
            automation_service.trigger_low_stock_alerts(state["low_stock_events"])
            append_event(state, "LOW_STOCK_ALERT_TRIGGERED", {"events": state["low_stock_events"]}, tool="create_low_stock_alert")

        # 4. Upsell recommendation (bonus feature)
        ordered_ids = [i["product_id"] for i in state["resolved_items"]]
        upsell = memory_service.get_upsell_recommendation(db, state["customer_id"], ordered_ids)
        if upsell:
            state["upsell_suggestion"] = upsell
            append_event(state, "UPSELL_RECOMMENDED", {"recommendation": upsell})

        return state
    finally:
        db.close()

# Node 10: Generate Confirmation from DB State
def generate_confirmation_node(state: AgentState) -> AgentState:
    if state["is_duplicate"] or state["status"] in ["needs_clarification", "pending_approval", "failed"]:
        return state

    db: Session = SessionLocal()
    try:
        conf_res = store_tools.send_confirmation(db, state["order_id"])
        base_msg = conf_res["confirmation_message"]

        # Append upsell if available (non-blocking)
        if state.get("upsell_suggestion"):
            base_msg += f"\n\n💡 *Tip*: {state['upsell_suggestion']['pitch']}"

        state["confirmation_message"] = base_msg
        state["status"] = "confirmed"
        state["tool_calls"].append({"tool": "send_confirmation", "order_id": state["order_id"]})
        append_event(state, "CONFIRMATION_GENERATED", {"order_id": state["order_id"]}, tool="send_confirmation")

        # Dispatch n8n notification webhook
        webhook_payload = {
            "order_id": state["order_id"],
            "customer_id": state["customer_id"],
            "customer_phone": state["customer_phone"],
            "message": state["confirmation_message"],
            "total": state["committed_order"]["total"]
        }
        automation_service.trigger_n8n_order_webhook(webhook_payload)
        append_event(state, "N8N_AUTOMATION_TRIGGERED", {"target": "WhatsApp_Confirmation"})

        return state
    finally:
        db.close()

# Node 11: Persist Agent Run History
def persist_run_node(state: AgentState) -> AgentState:
    db: Session = SessionLocal()
    try:
        append_event(state, "RUN_PERSISTED", {"run_id": state["run_id"], "status": state["status"]})

        agent_run = AgentRun(
            id=state["run_id"],
            request_id=state["request_id"],
            customer_id=state.get("customer_id"),
            status=state["status"],
            events=state["events"],
            input_text=state["input_text"],
            structured_intent=state.get("intent", {}),
            tool_calls=state.get("tool_calls", []),
            final_output={
                "message": state.get("confirmation_message"),
                "order_id": state.get("order_id"),
                "status": state["status"],
                "clarification_options": state.get("clarification_options"),
                "low_stock_events": state.get("low_stock_events")
            }
        )
        db.add(agent_run)
        db.commit()
        return state
    finally:
        db.close()

# Build LangGraph workflow
def build_kiranaos_agent():
    workflow = StateGraph(AgentState)

    # Add Nodes
    workflow.add_node("parse_request", parse_request_node)
    workflow.add_node("extract_items", extract_items_node)
    workflow.add_node("resolve_products", resolve_products_node)
    workflow.add_node("lookup_inventory_pricing", lookup_inventory_pricing_node)
    workflow.add_node("validate_availability", validate_availability_node)
    workflow.add_node("calculate_order", calculate_order_node)
    workflow.add_node("create_order", create_order_node)
    workflow.add_node("update_inventory", update_inventory_node)
    workflow.add_node("post_order_automations", post_order_automations_node)
    workflow.add_node("generate_confirmation", generate_confirmation_node)
    workflow.add_node("persist_run", persist_run_node)

    # Set Edges
    workflow.set_entry_point("parse_request")
    workflow.add_edge("parse_request", "extract_items")
    workflow.add_edge("extract_items", "resolve_products")
    workflow.add_edge("resolve_products", "lookup_inventory_pricing")
    workflow.add_edge("lookup_inventory_pricing", "validate_availability")
    workflow.add_edge("validate_availability", "calculate_order")
    workflow.add_edge("calculate_order", "create_order")
    workflow.add_edge("create_order", "update_inventory")
    workflow.add_edge("update_inventory", "post_order_automations")
    workflow.add_edge("post_order_automations", "generate_confirmation")
    workflow.add_edge("generate_confirmation", "persist_run")
    workflow.add_edge("persist_run", END)

    return workflow.compile()

kirana_operator = build_kiranaos_agent()

def run_agent_workflow(
    message: str,
    phone: str = "+919876543210",
    customer_id: Optional[str] = None,
    address: Optional[str] = None,
    idempotency_key: Optional[str] = None,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """Execute the compiled LangGraph workflow with full state persistence."""
    req_id = request_id or f"req_{uuid.uuid4().hex[:8]}"
    run_id = f"run_{uuid.uuid4().hex[:8]}"

    initial_state: AgentState = {
        "request_id": req_id,
        "run_id": run_id,
        "customer_id": customer_id or "",
        "customer_phone": phone,
        "customer_name": None,
        "input_text": message,
        "idempotency_key": idempotency_key,
        "delivery_address": address,
        "intent": {},
        "extracted_items": [],
        "resolved_items": [],
        "unresolved_items": [],
        "inventory_status": [],
        "pricing_status": {},
        "calculated_order": None,
        "approval_needed": False,
        "approval_reason": None,
        "approval_status": None,
        "order_id": None,
        "committed_order": None,
        "is_duplicate": False,
        "low_stock_events": [],
        "delivery_info": None,
        "upsell_suggestion": None,
        "confirmation_message": None,
        "status": "processing",
        "clarification_options": None,
        "events": [],
        "tool_calls": []
    }

    final_state = kirana_operator.invoke(initial_state)
    return final_state
