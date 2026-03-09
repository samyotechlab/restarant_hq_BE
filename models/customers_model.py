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
    country_code: str = Field(..., min_length=2, max_length=5, examples=["+91", "+1"])
    phone_number: str = Field(..., min_length=7, max_length=15, examples=["9876543210"])
    email: EmailStr
    address: str = Field(..., min_length=5, max_length=300)
    city: str = Field(..., min_length=2, max_length=100)
    pincode: str = Field(..., min_length=4, max_length=10, examples=["452001"])
    orders: List[str] = Field(default=[])
    status: CustomerStatus = Field(default=CustomerStatus.NEW)


class CustomerUpdate(BaseModel):
    """All fields are optional — supports partial (PATCH-style) updates."""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    country_code: Optional[str] = Field(None, min_length=2, max_length=5)
    phone_number: Optional[str] = Field(None, min_length=7, max_length=15)
    email: Optional[EmailStr] = None
    address: Optional[str] = Field(None, min_length=5, max_length=300)
    city: Optional[str] = Field(None, min_length=2, max_length=100)
    pincode: Optional[str] = Field(None, min_length=4, max_length=10)
    status: Optional[CustomerStatus] = None


class CustomerResponse(BaseModel):
    """Shape of the customer object returned to the client."""
    id: str
    customer_id: str
    name: str
    country_code: str
    phone_number: str
    email: EmailStr
    address: str
    city: str
    pincode: str
    orders: List[str] = []
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