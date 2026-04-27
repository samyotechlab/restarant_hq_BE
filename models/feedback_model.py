from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
from models.orders_model import OrderResponse



class FeedbackCreate(BaseModel):
    customer: Optional[str] = None              
    order: Optional[str] = None                 
    phone_number: Optional[str] = Field(None)
    overall_rating: Optional[int] = Field(default=1, ge=1, le=5)
    food_quality_rating: Optional[int] = Field(default=1, ge=1, le=5)
    delivery_rating: Optional[int] = Field(default=1, ge=1, le=5)
    comment: Optional[str] = Field(None)


class FeedbackUpdate(BaseModel):
    """All fields optional — supports partial updates."""
    customer: Optional[str] = None
    order: Optional[str] = None
    phone_number: Optional[str] = Field(None)
    overall_rating: Optional[int] = Field(default=1)
    food_quality_rating: Optional[int] = Field(default=1)
    delivery_rating: Optional[int] = Field(default=1)
    comment: Optional[str] = Field(None)


class PopulatedFeedbackCustomer(BaseModel):
    """Minimal customer details embedded in feedback response."""
    customer_id: Optional[str] = None
    name: Optional[str] = None
    country_code: Optional[str] = None
    phone_number: Optional[str] = None


class FeedbackResponse(BaseModel):
    id: str
    feedback_id: str                                            
    customer: Optional[PopulatedFeedbackCustomer] = None
    order: Optional[OrderResponse] = None
    phone_number: Optional[str] = None
    overall_rating: Optional[int] = 1
    food_quality_rating: Optional[int] = 1
    delivery_rating: Optional[int] = 1
    comment: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class PaginatedFeedbackResponse(BaseModel):
    """Wraps a page of feedback with metadata for the frontend."""
    total_results: int
    page: int
    limit: int
    total_pages: int
    data: List[FeedbackResponse]

