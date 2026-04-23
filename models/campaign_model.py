from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class Customer(BaseModel):
    name: Optional[str] = None
    country_code: Optional[str] = None
    phone_number: str
    status: Optional[str] = "Pending"


class CampaignCreate(BaseModel):
    campaign_image: Optional[str] = None
    title: str
    description: str
    customers: List[Customer] = Field(default_factory=list)
    is_sent: bool = False


class CampaignUpdate(BaseModel):
    campaign_image: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    customers: Optional[List[Customer]] = None
    is_sent: Optional[bool] = None


class CampaignResponse(BaseModel):
    id: str
    campaign_image: Optional[str] = None
    title: str
    description: str
    customers: List[Customer]
    is_sent: bool
    created_at: datetime
    updated_at: datetime


class PaginatedCampaignResponse(BaseModel):
    total_results: int
    page: int
    total_pages: int
    limit: int
    data: List[CampaignResponse]