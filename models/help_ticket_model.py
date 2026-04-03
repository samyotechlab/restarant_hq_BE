from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

from models.orders_model import OrderItemResponse, OrderStatus


class TicketStatus(str, Enum):
    OPEN = "open"
    PENDING = "pending"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TicketSource(str, Enum):
    MANUAL = "manual"
    AI_AGENT = "ai_agent"
    EMAIL = "email"


class HelpTicketCreate(BaseModel):
    """All fields optional — frontend handles required validation."""
    customer: Optional[str] = None
    order: Optional[str] = None              
    issue: Optional[str] = Field(None)
    status: Optional[TicketStatus] = Field(default=TicketStatus.OPEN)
    priority: Optional[TicketPriority] = Field(default=TicketPriority.LOW)
    category: Optional[str] = Field(None)
    assigned_agent: Optional[str] = Field(None)
    source: Optional[TicketSource] = Field(default=TicketSource.MANUAL)


class HelpTicketUpdate(BaseModel):
    """All fields optional — supports partial updates."""
    customer: Optional[str] = None
    order: Optional[str] = None       
    issue: Optional[str] = Field(None)
    status: Optional[TicketStatus] = None
    priority: Optional[TicketPriority] = None
    category: Optional[str] = Field(None)
    assigned_agent: Optional[str] = Field(None)
    source: Optional[TicketSource] = None


class PopulatedTicketCustomer(BaseModel):
    """Minimal customer details embedded in help ticket response."""
    id: Optional[str] = None
    customer_id: Optional[str] = None
    name: Optional[str] = None
    country_code: Optional[str] = None
    phone_number: Optional[str] = None


class PopulatedTicketOrder(BaseModel):
    """Minimal order details embedded in help ticket response."""
    id: str = Field(..., alias="id")
    order_id: str
    status: OrderStatus
    grand_total: Optional[float] = None
    items: List[OrderItemResponse] = []


class HelpTicketResponse(BaseModel):
    """Shape of the help ticket returned to the client."""
    id: str
    ticket_id: str                              
    customer: Optional[PopulatedTicketCustomer] = None
    order: Optional[PopulatedTicketOrder] = None
    issue: Optional[str] = None
    status: Optional[TicketStatus] = None
    priority: Optional[TicketPriority] = None
    category: Optional[str] = None
    assigned_agent: Optional[str] = None
    source: Optional[TicketSource] = None
    created_at: datetime
    updated_at: datetime


class PaginatedHelpTicketResponse(BaseModel):
    """Wraps a page of help tickets with metadata for the frontend."""
    total_results: int
    page: int
    limit: int
    total_pages: int
    data: List[HelpTicketResponse]