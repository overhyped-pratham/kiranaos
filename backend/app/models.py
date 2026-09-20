import datetime
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    Text,
    DateTime,
    ForeignKey,
    JSON,
    CheckConstraint
)
from sqlalchemy.orm import relationship
from backend.app.database import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(String(50), primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    brand = Column(String(100), nullable=False, index=True)
    category = Column(String(100), nullable=False, index=True)
    size = Column(String(50), nullable=False)
    unit = Column(String(20), nullable=False, default="packet")
    price = Column(Float, nullable=False)
    stock = Column(Integer, nullable=False, default=0)
    low_stock_threshold = Column(Integer, nullable=False, default=5)
    aliases = Column(JSON, nullable=False, default=list)  # multilingual aliases, spelling variants
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Invariant: stock cannot go negative
    __table_args__ = (
        CheckConstraint("stock >= 0", name="check_stock_non_negative"),
    )

    order_items = relationship("OrderItem", back_populates="product")
    inventory_logs = relationship("InventoryLog", back_populates="product")


class Customer(Base):
    __tablename__ = "customers"

    id = Column(String(50), primary_key=True, index=True)
    phone = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    default_address = Column(Text, nullable=True)
    preferences = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    orders = relationship("Order", back_populates="customer")
    customer_preferences = relationship("CustomerPreference", back_populates="customer")


class Order(Base):
    __tablename__ = "orders"

    id = Column(String(50), primary_key=True, index=True)  # e.g., ORD-20260920-001
    customer_id = Column(String(50), ForeignKey("customers.id"), nullable=False, index=True)
    status = Column(String(30), nullable=False, default="confirmed")  # confirmed, pending_approval, rejected, cancelled
    subtotal = Column(Float, nullable=False)
    delivery_charge = Column(Float, nullable=False, default=20.0)
    total = Column(Float, nullable=False)
    idempotency_key = Column(String(100), unique=True, index=True, nullable=True)
    delivery_status = Column(String(30), nullable=False, default="requested")  # requested, assigned, dispatched, delivered
    delivery_address = Column(Text, nullable=True)
    approval_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    customer = relationship("Customer", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    delivery_requests = relationship("DeliveryRequest", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String(50), ForeignKey("orders.id"), nullable=False, index=True)
    product_id = Column(String(50), ForeignKey("products.id"), nullable=False, index=True)
    product_name = Column(String(200), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    line_total = Column(Float, nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")


class InventoryLog(Base):
    __tablename__ = "inventory_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(String(50), ForeignKey("products.id"), nullable=False, index=True)
    order_id = Column(String(50), nullable=True, index=True)
    change_amount = Column(Integer, nullable=False)  # e.g. -2 or +20
    previous_stock = Column(Integer, nullable=False)
    new_stock = Column(Integer, nullable=False)
    reason = Column(String(100), nullable=False)  # order_fulfillment, restock, manual_override, failed_rollback
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    product = relationship("Product", back_populates="inventory_logs")


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id = Column(String(50), primary_key=True, index=True)
    request_id = Column(String(100), nullable=False, index=True)
    customer_id = Column(String(50), nullable=True, index=True)
    status = Column(String(30), nullable=False)  # completed, needs_clarification, pending_approval, failed
    events = Column(JSON, nullable=False, default=list)  # chronological timeline events
    input_text = Column(Text, nullable=False)
    structured_intent = Column(JSON, nullable=False, default=dict)
    tool_calls = Column(JSON, nullable=False, default=list)
    final_output = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class CustomerPreference(Base):
    __tablename__ = "customer_preferences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(String(50), ForeignKey("customers.id"), nullable=False, index=True)
    product_id = Column(String(50), ForeignKey("products.id"), nullable=False, index=True)
    frequency = Column(Integer, nullable=False, default=1)
    preferred_quantity = Column(Integer, nullable=False, default=1)
    last_ordered_at = Column(DateTime, default=datetime.datetime.utcnow)

    customer = relationship("Customer", back_populates="customer_preferences")
    product = relationship("Product")


class LowStockEvent(Base):
    __tablename__ = "low_stock_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(String(50), ForeignKey("products.id"), nullable=False, index=True)
    stock_at_event = Column(Integer, nullable=False)
    threshold = Column(Integer, nullable=False)
    status = Column(String(30), nullable=False, default="alert_triggered")
    triggered_at = Column(DateTime, default=datetime.datetime.utcnow)

    product = relationship("Product")


class DeliveryRequest(Base):
    __tablename__ = "delivery_requests"

    id = Column(String(50), primary_key=True, index=True)
    order_id = Column(String(50), ForeignKey("orders.id"), nullable=False, index=True)
    address = Column(Text, nullable=False)
    status = Column(String(30), nullable=False, default="dispatched")  # requested, assigned, out_for_delivery, delivered
    delivery_partner = Column(String(100), nullable=False, default="Kirana Express Rider")
    estimated_time = Column(String(50), nullable=False, default="15-25 mins")
    tracking_id = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    order = relationship("Order", back_populates="delivery_requests")
