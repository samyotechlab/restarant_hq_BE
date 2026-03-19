from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class OrderStatus(str, Enum):
    PENDING = "Pending"
    PREPARING = "Preparing"
    READY = "Ready"
    SERVED = "Served"
    COMPLETED = "Completed"


class PaymentMethod(str, Enum):
    CASH = "Cash"
    CARD = "Card"
    ONLINE = "Online"
    PENDING = "Pending"


# ── sub-model for each item in the order (used in create/update) ──
class OrderItem(BaseModel):
    """A single item inside an order — sent by the frontend."""
    menu_item: str                              # MongoDB ObjectId of the menu item as string
    price: Optional[float] = None
    quantity: Optional[int] = Field(None, gt=0)
    sub_total: Optional[float] = None


# ── populated menu item inside order response ──
class OrderItemResponse(BaseModel):
    """A single item inside an order response — menu_item is populated."""
    menu_item_id: str                           # original ObjectId stored
    item_no: Optional[str] = None
    item_name: Optional[str] = None
    image: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    quantity: Optional[int] = None
    sub_total: Optional[float] = None


# ── populated customer inside order response ──
class PopulatedCustomer(BaseModel):
    """Customer details embedded in order response."""
    customer_id: Optional[str] = None
    name: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None


class OrderCreate(BaseModel):
    """All fields optional — frontend handles required validation."""
    customer: Optional[str] = None              # MongoDB ObjectId of customer as string
    items: Optional[List[OrderItem]] = []
    status: Optional[OrderStatus] = Field(default=OrderStatus.PENDING)
    sub_total: Optional[float] = None
    tax: Optional[float] = None
    discount: Optional[float] = None
    grand_total: Optional[float] = None
    notes: Optional[str] = None
    payment_method: Optional[PaymentMethod] = Field(default=PaymentMethod.PENDING)
    is_paid: Optional[bool] = Field(default=False)


class OrderUpdate(BaseModel):
    """All fields optional — supports partial updates."""
    customer: Optional[str] = None
    items: Optional[List[OrderItem]] = None
    status: Optional[OrderStatus] = None
    sub_total: Optional[float] = None
    tax: Optional[float] = None
    discount: Optional[float] = None
    grand_total: Optional[float] = None
    notes: Optional[str] = None
    payment_method: Optional[PaymentMethod] = None
    is_paid: Optional[bool] = None


class OrderResponse(BaseModel):
    """Shape of the order returned to the client — customer and items are populated."""
    id: str
    order_id: str                               # server-generated e.g. ORD-3F9A1B2C
    customer: Optional[PopulatedCustomer] = None
    items: List[OrderItemResponse] = []
    status: OrderStatus
    sub_total: Optional[float] = None
    tax: Optional[float] = None
    discount: Optional[float] = None
    grand_total: Optional[float] = None
    notes: Optional[str] = None
    payment_method: PaymentMethod
    is_paid: bool
    created_at: datetime
    updated_at: datetime


class PaginatedOrderResponse(BaseModel):
    """Wraps a page of orders with metadata for the frontend."""
    total_results: int
    page: int
    limit: int
    total_pages: int
    data: List[OrderResponse]