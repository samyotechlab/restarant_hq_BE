from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class ServiceCreate(BaseModel):
    """Payload the client sends when creating a new service."""
    service_name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, min_length=2, max_length=500)
    pricing: Optional[str] = Field(None, min_length=1, max_length=200)
    coverage_area: Optional[str] = Field(None, min_length=2, max_length=200)
    is_active: bool = Field(default=True)


class ServiceUpdate(BaseModel):
    """All fields optional — supports partial updates."""
    service_name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, min_length=2, max_length=500)
    pricing: Optional[str] = Field(None, min_length=1, max_length=200)
    coverage_area: Optional[str] = Field(None, min_length=2, max_length=200)
    is_active: Optional[bool] = None


class ServiceResponse(BaseModel):
    """Shape of the service object returned to the client."""
    id: str
    service_id: str             
    service_name: str
    description: str
    pricing: str
    coverage_area: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PaginatedServiceResponse(BaseModel):
    """Wraps a page of services with metadata for the frontend."""
    total_results: int
    page: int
    limit: int
    total_pages: int
    data: List[ServiceResponse]