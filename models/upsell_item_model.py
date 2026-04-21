from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class UpsellItemCreate(BaseModel):
  item: str
  original_price: Optional[float] = None
  offer_price: Optional[float] = None
  offer_percentage: Optional[float] = None
  available: Optional[bool] = Field(default=False)



class PopulateMenuItemOffer(BaseModel):
  menu_item_id:  Optional[str]   = None
  item_no:       Optional[str]   = None
  item_name:     Optional[str]   = None
  category:      Optional[str]   = None
  base_price:    Optional[float] = None
  online_price:  Optional[float] = None
  dietary:       Optional[str]   = None
  available:     Optional[bool]  = None


class UpsellItemUpdate(BaseModel):
  item: Optional[str] = None
  original_price: Optional[float] = None
  offer_price: Optional[float] = None
  offer_percentage: Optional[float] = None
  available: Optional[bool]


class UpsellItemResponse(BaseModel):
  id: str
  item: PopulateMenuItemOffer | None
  original_price: float
  offer_price: float
  offer_percentage: float
  available: bool
  created_at: datetime
  updated_at: datetime


class PaginatedUpsellItemResponse(BaseModel):
  total_results: int
  page:          int
  limit:         int
  total_pages:   int
  data:          List[UpsellItemResponse]