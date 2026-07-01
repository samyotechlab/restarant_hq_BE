from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class Customer(BaseModel):
    name: Optional[str] = None
    country_code: Optional[str] = None
    phone_number: str
    status: Optional[str] = "Pending"
    address: Optional[str] = None
    sent_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    fail_reason: Optional[str] = None


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
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    # ── Stats (computed, not stored in DB) ──
    total_customers: int = 0
    sent_count: int = 0
    read_count: int = 0
    failed_count: int = 0
    error_count: int = 0


class PaginatedCampaignResponse(BaseModel):
    total_results: int
    page: int
    total_pages: int
    limit: int
    data: List[CampaignResponse]