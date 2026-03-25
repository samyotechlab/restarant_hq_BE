from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class CampaignType(str, Enum):
    COMBO = "combo"
    DISCOUNT = "discount"


class CampaignStatus(str, Enum):
    ACTIVE = "active"
    SCHEDULED = "scheduled"
    COMPLETED = "completed"


class CampaignCreate(BaseModel):
    """All fields optional — frontend handles required validation."""
    campaign_type: Optional[CampaignType] = None
    campaign_name: Optional[str] = Field(None)
    description: Optional[str] = Field(None)
    menu_items: Optional[List[str]] = []
    offer_price: Optional[float] = Field(default=0)
    discount_percentage: Optional[float] = Field(default=0)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: Optional[CampaignStatus] = Field(default=CampaignStatus.SCHEDULED)


class CampaignUpdate(BaseModel):
    """All fields optional — supports partial updates."""
    campaign_type: Optional[CampaignType] = None
    campaign_name: Optional[str] = Field(None)
    description: Optional[str] = Field(None)
    menu_items: Optional[List[str]] = None
    offer_price: Optional[float] = None
    discount_percentage: Optional[float] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: Optional[CampaignStatus] = None


class PopulatedMenuItem(BaseModel):
    """Minimal menu item details embedded in campaign response."""
    menu_item_id: str
    item_name: Optional[str] = None
    price: Optional[float] = None
    category: Optional[str] = None


class CampaignResponse(BaseModel):
    """Shape of the campaign returned to the client."""
    id: str
    campaign_id: str
    campaign_type: Optional[CampaignType] = None
    campaign_name: Optional[str] = None
    description: Optional[str] = None
    menu_items: List[PopulatedMenuItem] = []
    offer_price: Optional[float] = None
    discount_percentage: Optional[float] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: Optional[CampaignStatus] = None
    created_at: datetime
    updated_at: datetime


class PaginatedCampaignResponse(BaseModel):
    """Wraps a page of campaigns with metadata for the frontend."""
    total_results: int
    page: int
    limit: int
    total_pages: int
    data: List[CampaignResponse]

    