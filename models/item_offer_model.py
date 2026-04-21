from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class ItemOfferCreate(BaseModel):
  item: str
  base_price: Optional[float] = None
  offer_price: Optional[float] = None
  offer_percentage: Optional[float] = None



class PopulateMenuItemOffer(BaseModel):
  menu_item_id:  Optional[str]   = None
  item_no:       Optional[str]   = None
  item_name:     Optional[str]   = None
  category:      Optional[str]   = None
  base_price:    Optional[float] = None
  online_price:  Optional[float] = None
  dietary:       Optional[str]   = None
  available:     Optional[bool]  = None


class ItemOfferUpdate(BaseModel):
  item: Optional[str] = None
  base_price: Optional[float] = None
  offer_price: Optional[float] = None
  offer_percentage: Optional[float] = None



class ItemOfferResponse(BaseModel):
  id: str
  item: PopulateMenuItemOffer | None
  base_price: float
  offer_price: float
  offer_percentage: float
  created_at: datetime
  updated_at: datetime


class PaginatedItemOfferResponse(BaseModel):
  total_results: int
  page:          int
  limit:         int
  total_pages:   int
  data:          List[ItemOfferResponse]