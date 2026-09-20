from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class ProductBase(BaseModel):
    name: str
    brand: str
    category: str
    size: str
    unit: str = "packet"
    price: float
    stock: int
    low_stock_threshold: int = 5
    aliases: List[str] = []
    active: bool = True

class ProductCreate(ProductBase):
    id: str

class ProductUpdate(BaseModel):
    price: Optional[float] = None
    stock: Optional[int] = None
    low_stock_threshold: Optional[int] = None
    active: Optional[bool] = None

class ProductResponse(ProductBase):
    id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class RestockRequest(BaseModel):
    product_id: str
    quantity: int
    reason: str = "manual_restock"

class CustomerBase(BaseModel):
    phone: str
    name: str
    default_address: Optional[str] = None
    preferences: Dict[str, Any] = {}

class CustomerCreate(CustomerBase):
    id: str

class CustomerResponse(CustomerBase):
    id: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class OrderItemSchema(BaseModel):
    product_id: str
    product_name: str
    quantity: int
    unit_price: float
    line_total: float

    class Config:
        from_attributes = True

class OrderResponse(BaseModel):
    id: str
    customer_id: str
    status: str
    subtotal: float
    delivery_charge: float
    total: float
    idempotency_key: Optional[str] = None
    delivery_status: str
    delivery_address: Optional[str] = None
    approval_reason: Optional[str] = None
    items: List[OrderItemSchema] = []
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class TimelineEvent(BaseModel):
    timestamp: str
    event: str
    tool: Optional[str] = None
    details: Dict[str, Any] = {}

class AgentRunRequest(BaseModel):
    message: str
    phone: Optional[str] = "+919876543210"
    customer_id: Optional[str] = None
    address: Optional[str] = None
    idempotency_key: Optional[str] = None
    request_id: Optional[str] = None

class AgentApproveRequest(BaseModel):
    order_id: str
    action: str = Field(..., description="'approve' or 'reject'")
    reason: Optional[str] = None

class AgentRunResponse(BaseModel):
    run_id: str
    request_id: str
    customer_id: Optional[str] = None
    status: str  # confirmed, needs_clarification, pending_approval, failed, duplicate_ignored
    message: str
    order: Optional[OrderResponse] = None
    clarification_options: Optional[List[Dict[str, Any]]] = None
    low_stock_events: Optional[List[Dict[str, Any]]] = None
    events: List[TimelineEvent] = []
    structured_intent: Optional[Dict[str, Any]] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None

class WhatsAppWebhookMessage(BaseModel):
    from_number: str
    body: str
    message_id: str
    timestamp: Optional[str] = None
