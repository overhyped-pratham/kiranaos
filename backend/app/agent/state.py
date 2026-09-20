from typing import TypedDict, List, Dict, Any, Optional

class AgentState(TypedDict):
    request_id: str
    run_id: str
    customer_id: str
    customer_phone: str
    customer_name: Optional[str]
    input_text: str
    idempotency_key: Optional[str]
    delivery_address: Optional[str]
    
    # NLP & Semantic stages
    intent: Dict[str, Any]
    extracted_items: List[Dict[str, Any]]
    resolved_items: List[Dict[str, Any]]
    unresolved_items: List[Dict[str, Any]]
    
    # Live Database validation stages
    inventory_status: List[Dict[str, Any]]
    pricing_status: Dict[str, Any]
    calculated_order: Optional[Dict[str, Any]]
    
    # Approval & Gateways
    approval_needed: bool
    approval_reason: Optional[str]
    approval_status: Optional[str]  # "pending", "approved", "rejected"
    
    # Mutations & Commitments
    order_id: Optional[str]
    committed_order: Optional[Dict[str, Any]]
    is_duplicate: bool
    
    # Post-order events
    low_stock_events: List[Dict[str, Any]]
    delivery_info: Optional[Dict[str, Any]]
    upsell_suggestion: Optional[Dict[str, Any]]
    
    # Outputs & Timeline
    confirmation_message: Optional[str]
    status: str  # "confirmed", "needs_clarification", "pending_approval", "failed", "duplicate_ignored"
    clarification_options: Optional[List[Dict[str, Any]]]
    events: List[Dict[str, Any]]
    tool_calls: List[Dict[str, Any]]
