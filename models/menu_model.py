from datetime import datetime
from enum import Enum
from typing import Any, List, Optional
from pydantic import BaseModel, Field
import re


def _make_search_name(name: str) -> str:
    if not name:
        return ""
    name = name.lower()
    name = re.sub(r"[^\w\s]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


class MenuItemType(str, Enum):
    VEG = "Veg"
    NON_VEG = "Non-Veg"


class MenuItemCreate(BaseModel):
    """
    Payload for creating a menu item (API or CSV upload).

    CSV Column Mapping:
      CategoryName        → category
      ItemName            → item_name
      ItemDescription     → description
      ItemBasePrice       → base_price
      Dietary             → dietary        ('veg' → Veg, 'non-veg' → Non-Veg)
      Unit of sale        → unit_of_sale
      Online Price        → online_price
      Options             → options        (comma-separated → List[str])
      Upsell              → upsell
      Online Availability → available      ('Yes' → True, 'No' → False)
    """
    item_name: str = Field(...)
    search_name: Optional[str] = None
    category: str = Field(...)
    description: Optional[str] = Field(None)
    base_price: float = Field(..., ge=0)
    online_price: float = Field(..., ge=0)
    dietary: MenuItemType
    unit_of_sale: Optional[str] = Field(None, description="e.g. Per Plate, Per Kg, Per Pcs")
    options: Optional[List[str]] = Field(None, description="e.g. ['Regular', 'Cheese', 'Grilled']")
    upsell: Optional[str] = Field(None, description="e.g. Extra Chatni, Extra Pav")
    available: bool = Field(default=True)


class MenuItemUpdate(BaseModel):
    """All fields optional — supports partial updates via PATCH."""
    item_name: Optional[str] = Field(None)
    search_name: Optional[str] = None
    category: Optional[str] = Field(None)
    description: Optional[str] = Field(None)
    base_price: Optional[float] = Field(None, ge=0)
    online_price: Optional[float] = Field(None, ge=0)
    dietary: Optional[MenuItemType] = None
    unit_of_sale: Optional[str] = None
    options: Optional[List[str]] = None
    upsell: Optional[str] = None
    available: Optional[bool] = None


class MenuItemResponse(BaseModel):
    """Full shape of menu item returned to client."""
    id: str
    item_no: str
    item_name: str
    search_name: Optional[str] = None
    category: str
    description: Optional[str] = None
    base_price: float
    online_price: float
    dietary: MenuItemType
    unit_of_sale: Optional[str] = None
    options: Optional[List[str]] = None
    upsell: Optional[str] = None
    available: bool
    created_at: datetime
    updated_at: datetime


class PaginatedMenuResponse(BaseModel):
    """Paginated list of menu items."""
    total_results: int
    page: int
    limit: int
    total_pages: int
    data: List[MenuItemResponse]


# ─────────────────────────────────────────────────────────────────
# Bulk Upload Response Models
# ─────────────────────────────────────────────────────────────────

class BulkMenuUploadResult(BaseModel):
    """Per-row result for a bulk upload."""
    index: int
    success: bool
    item_name: Optional[str] = None
    item: Optional[MenuItemResponse] = None
    error: Optional[str] = None


class BulkMenuUploadResponse(BaseModel):
    """Summary returned after bulk upload."""
    total: int
    inserted: int
    updated: int
    failed: int
    skipped: int = 0
    results: List[BulkMenuUploadResult]


TYPE_NORMALIZE_MAP = {
    "veg":            MenuItemType.VEG,
    "vegetarian":     MenuItemType.VEG,
    "non-veg":        MenuItemType.NON_VEG,
    "nonveg":         MenuItemType.NON_VEG,
    "non veg":        MenuItemType.NON_VEG,
    "non-vegetarian": MenuItemType.NON_VEG,
    "nonvegetarian":  MenuItemType.NON_VEG,
}


def _s(val: Any) -> Optional[str]:
    """Safe string — returns None for nan/empty/None."""
    if val is None:
        return None
    s = str(val).strip()
    return s if s and s.lower() not in ("nan", "none", "") else None


def _f(val: Any) -> Optional[float]:
    """Safe positive float — returns None for non-numeric or negative."""
    try:
        v = float(val)
        return v if v >= 0 else None
    except (TypeError, ValueError):
        return None


def _parse_options(val: Any) -> Optional[List[str]]:
    """
    Parse comma-separated options string → List[str].
    e.g. "Regular, Cheese/Grilled, 24 AED" → ["Regular", "Cheese/Grilled", "24 AED"]
    Returns None if empty/null.
    """
    raw = _s(val)
    if not raw:
        return None
    return [opt.strip() for opt in raw.split(",") if opt.strip()]


class CSVMenuRow(BaseModel):
    """
    Maps the 10 columns from MenuAI_Final_Updated.xlsx.
    Call .to_menu_item_create() to get a validated MenuItemCreate.

    Columns:
      CategoryName        → category
      ItemName            → item_name
      ItemDescription     → description
      ItemBasePrice       → base_price
      Dietary             → dietary
      Unit of sale        → unit_of_sale
      Online Price        → online_price
      Options             → options        (comma-separated → List[str])
      Upsell              → upsell
      Online Availability → available
    """
    CategoryName: Optional[str] = None
    ItemName: Optional[str] = None
    ItemDescription: Optional[str] = None
    ItemBasePrice: Optional[Any] = None
    Dietary: Optional[str] = None
    Unit_of_sale: Optional[str] = Field(None, alias="Unit of sale")
    Online_Price: Optional[Any] = Field(None, alias="Online Price")
    Options: Optional[Any] = None
    Upsell: Optional[str] = None
    Online_Availability: Optional[str] = Field(None, alias="Online Availability")

    model_config = {"populate_by_name": True, "extra": "allow"}

    def to_menu_item_create(self) -> MenuItemCreate:
        """
        Convert raw CSV row → validated MenuItemCreate.
        Raises ValueError with a clear message on failure.
        """
        name = _s(self.ItemName)
        if not name:
            raise ValueError("ItemName is missing or empty.")

        category = _s(self.CategoryName)
        if not category:
            raise ValueError(f"CategoryName missing for '{name}'.")

        base_price = _f(self.ItemBasePrice)
        if base_price is None:
            raise ValueError(f"ItemBasePrice missing or invalid for '{name}'.")

        online_price = _f(self.Online_Price)
        if online_price is None:
            raise ValueError(f"Online Price missing or invalid for '{name}'.")

        raw_type = _s(self.Dietary) or "veg"
        item_type = TYPE_NORMALIZE_MAP.get(raw_type.lower(), MenuItemType.VEG)

        available_raw = _s(self.Online_Availability) or "No"
        available = available_raw.strip().lower() == "yes"

        return MenuItemCreate(
            item_name=name,
            search_name=_make_search_name(name),
            category=category,
            description=_s(self.ItemDescription),
            base_price=base_price,
            online_price=online_price,
            dietary=item_type,
            unit_of_sale=_s(self.Unit_of_sale),
            options=_parse_options(self.Options),
            upsell=_s(self.Upsell),
            available=available,
        )