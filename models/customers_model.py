from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field


class CustomerStatus(str, Enum):
    NEW = "new"
    ACTIVE = "active"
    INACTIVE = "inactive"
    VIP = "vip"


class CustomerCreate(BaseModel):
    """Payload the client sends when registering a new customer."""
    name: str = Field(..., min_length=2, max_length=100)
    country_code: Optional[str] = Field(None)
    phone_number: str = Field(..., min_length=7, max_length=15, examples=["9876543210"])
    email: Optional[str] = None
    address: Optional[str] = Field(None)
    city: Optional[str] = Field(None)
    pincode: Optional[str] = Field(None)
    orders: List[str] = Field(default=[])
    status: CustomerStatus = Field(default=CustomerStatus.NEW)


class CustomerUpdate(BaseModel):
    """All fields are optional — supports partial (PATCH-style) updates."""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    country_code: Optional[str] = Field(None)
    phone_number: Optional[str] = Field(None, min_length=7, max_length=15)
    email: Optional[str] = None
    address: Optional[str] = Field(None)
    city: Optional[str] = Field(None)
    pincode: Optional[str] = Field(None)
    status: Optional[CustomerStatus] = None

class PopulatedOrder(BaseModel):
    """Minimal order details embedded inside a customer response."""
    order_id: str
    grand_total: Optional[float] = None

class CustomerResponse(BaseModel):
    """Shape of the customer object returned to the client."""
    id: str
    customer_id: str
    name: str
    country_code: Optional[str] = None
    phone_number: str
    email: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    pincode: Optional[str] = None
    orders: List[PopulatedOrder] = []
    status: CustomerStatus
    created_at: datetime
    updated_at: datetime


class BulkUploadResult(BaseModel):
    """Result for a single customer in a bulk upload — succeeded or failed."""
    index: int                          
    success: bool
    customer: Optional[CustomerResponse] = None  
    error: Optional[str] = None                  


class BulkUploadResponse(BaseModel):
    """Summary returned after a bulk upload attempt."""
    total: int
    inserted: int
    failed: int
    results: List[BulkUploadResult]


class PaginatedCustomerResponse(BaseModel):
    """Wraps a page of customers with metadata for the frontend."""
    total_results: int         
    page: int           
    limit: int         
    total_pages: int    
    data: List[CustomerResponse]

