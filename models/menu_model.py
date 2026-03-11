from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, HttpUrl, Field


class MenuItemType(str, Enum):
    VEG = "Veg"
    NON_VEG = "Non-Veg"


class MenuItemCreate(BaseModel):
    """Payload the client sends when creating a new menu item."""
    image: Optional[HttpUrl] = None
    item_name: str = Field(..., min_length=2, max_length=100)
    category: str = Field(..., min_length=2, max_length=100)
    price: int = Field(..., gt=0)
    type: MenuItemType
    offer: Optional[str] = None
    available: bool = Field(default=True)


class MenuItemUpdate(BaseModel):
    """All fields optional — supports partial updates."""
    image: Optional[HttpUrl] = None
    item_name: Optional[str] = Field(None, min_length=2, max_length=100)
    category: Optional[str] = Field(None, min_length=2, max_length=100)
    price: Optional[int] = Field(None, gt=0)
    type: Optional[MenuItemType] = None
    offer: Optional[str] = Field(None)
    available: Optional[bool] = None


class MenuItemResponse(BaseModel):
    """Shape of the menu item returned to the client."""
    id: str
    item_no: str = Field(..., min_length=3)
    image: Optional[str] = None
    item_name: str
    category: str
    price: int
    type: MenuItemType
    offer: str
    available: bool
    created_at: datetime
    updated_at: datetime


class PaginatedMenuResponse(BaseModel):
    """Wraps a page of menu items with metadata for the frontend."""
    total_results: int
    page: int
    limit: int
    total_pages: int
    data: List[MenuItemResponse]


class BulkMenuUploadResult(BaseModel):
    """Result for a single item in a bulk upload — succeeded or failed."""
    index: int
    success: bool
    item: Optional[MenuItemResponse] = None
    error: Optional[str] = None


class BulkMenuUploadResponse(BaseModel):
    """Summary returned after a bulk menu upload attempt."""
    total: int
    inserted: int
    failed: int
    results: List[BulkMenuUploadResult]