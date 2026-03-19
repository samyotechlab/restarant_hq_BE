from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class EnquiryStatus(str, Enum):
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    CONVERTED = "converted"
    CLOSED = "closed"


class EnquiryCreate(BaseModel):
    """All fields optional — frontend handles required validation."""
    name: Optional[str] = Field(None)
    country_code: Optional[str] = Field(None)
    phone_number: Optional[str] = Field(None)
    service: Optional[str] = Field(None)
    source: Optional[str] = Field(None)
    status: Optional[EnquiryStatus] = Field(default=EnquiryStatus.NEW)
    assigned_to: Optional[str] = Field(None)


class EnquiryUpdate(BaseModel):
    """All fields optional — supports partial updates."""
    name: Optional[str] = Field(None)
    country_code: Optional[str] = Field(None)
    phone_number: Optional[str] = Field(None)
    service: Optional[str] = Field(None)
    source: Optional[str] = Field(None)
    status: Optional[EnquiryStatus] = None
    assigned_to: Optional[str] = Field(None)


class EnquiryResponse(BaseModel):
    """Shape of the enquiry object returned to the client."""
    id: str
    enquiry_id: str
    name: Optional[str] = None
    country_code: Optional[str] = None
    phone_number: Optional[str] = None
    service: Optional[str] = None
    source: Optional[str] = None
    status: EnquiryStatus
    assigned_to: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class PaginatedEnquiryResponse(BaseModel):
    """Wraps a page of enquiries with metadata for the frontend."""
    total_results: int
    page: int
    limit: int
    total_pages: int
    data: List[EnquiryResponse]