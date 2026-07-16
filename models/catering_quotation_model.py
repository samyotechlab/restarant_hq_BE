from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class CreateCateringQuotation(BaseModel):
    name: str
    service_address: str
    service_date: str
    service_time: str
    quotation_no: str
    prepared_date: str
    prepared_by: str

    estimated_pax: int = Field(ge=1)
    food_cost_per_pax: float = Field(ge=0)
    std_margin_per_pax: float = Field(ge=0)
    quoted_price_per_pax: float = Field(ge=0)
    approved_by: Optional[str] = None

    revenue_notes: Optional[str] = None
    menu_file_url: Optional[str] = None
    menu_file_name: Optional[str] = None

    revenue_qty: float = Field(ge=0)
    revenue_rate: float = Field(ge=0)
    total_revenue: float = Field(ge=0)

    food_cost_qty: float = Field(ge=0)
    food_cost_rate: float = Field(ge=0)
    food_cost: float = Field(ge=0)

    staff_cost_qty: float = Field(ge=0)
    staff_cost_rate: float = Field(ge=0)
    staff_cost: float = Field(ge=0)

    full_day_service_qty: float = Field(ge=0)
    full_day_service_rate: float = Field(ge=0)
    full_day_service: float = Field(ge=0)

    half_day_service_qty: float = Field(ge=0)
    half_day_service_rate: float = Field(ge=0)
    half_day_service: float = Field(ge=0)

    outsourced_service_qty: float = Field(ge=0)
    outsourced_service_rate: float = Field(ge=0)
    outsourced_service: float = Field(ge=0)

    transport_qty: float = Field(ge=0)
    transport_rate: float = Field(ge=0)
    transport: float = Field(ge=0)

    decoration_qty: float = Field(ge=0)
    decoration_rate: float = Field(ge=0)
    decoration: float = Field(ge=0)

    glasses_etc_qty: float = Field(ge=0)
    glasses_etc_rate: float = Field(ge=0)
    glasses_etc: float = Field(ge=0)

    other_rentals_qty: float = Field(ge=0)
    other_rentals_rate: float = Field(ge=0)
    other_rentals: float = Field(ge=0)

    total_c2: float = Field(default=0, ge=0)
    total_c3: float = Field(default=0, ge=0)
    total_costs: float = Field(default=0, ge=0)
    gross_profit: float = 0
    gross_margin_pct: float = 0

    notes: Optional[str] = None
    status: str = "pending"


class UpdateCateringQuotation(BaseModel):
    name: Optional[str] = None
    service_address: Optional[str] = None
    service_date: Optional[str] = None
    service_time: Optional[str] = None
    quotation_no: Optional[str] = None
    prepared_date: Optional[str] = None
    prepared_by: Optional[str] = None

    estimated_pax: Optional[int] = Field(default=None, ge=1)
    food_cost_per_pax: Optional[float] = Field(default=None, ge=0)
    std_margin_per_pax: Optional[float] = Field(default=None, ge=0)
    quoted_price_per_pax: Optional[float] = Field(default=None, ge=0)
    approved_by: Optional[str] = None

    revenue_notes: Optional[str] = None
    menu_file_url: Optional[str] = None
    menu_file_name: Optional[str] = None

    revenue_qty: Optional[float] = Field(default=None, ge=0)
    revenue_rate: Optional[float] = Field(default=None, ge=0)
    total_revenue: Optional[float] = Field(default=None, ge=0)

    food_cost_qty: Optional[float] = Field(default=None, ge=0)
    food_cost_rate: Optional[float] = Field(default=None, ge=0)
    food_cost: Optional[float] = Field(default=None, ge=0)

    staff_cost_qty: Optional[float] = Field(default=None, ge=0)
    staff_cost_rate: Optional[float] = Field(default=None, ge=0)
    staff_cost: Optional[float] = Field(default=None, ge=0)

    full_day_service_qty: Optional[float] = Field(default=None, ge=0)
    full_day_service_rate: Optional[float] = Field(default=None, ge=0)
    full_day_service: Optional[float] = Field(default=None, ge=0)

    half_day_service_qty: Optional[float] = Field(default=None, ge=0)
    half_day_service_rate: Optional[float] = Field(default=None, ge=0)
    half_day_service: Optional[float] = Field(default=None, ge=0)

    outsourced_service_qty: Optional[float] = Field(default=None, ge=0)
    outsourced_service_rate: Optional[float] = Field(default=None, ge=0)
    outsourced_service: Optional[float] = Field(default=None, ge=0)

    transport_qty: Optional[float] = Field(default=None, ge=0)
    transport_rate: Optional[float] = Field(default=None, ge=0)
    transport: Optional[float] = Field(default=None, ge=0)

    decoration_qty: Optional[float] = Field(default=None, ge=0)
    decoration_rate: Optional[float] = Field(default=None, ge=0)
    decoration: Optional[float] = Field(default=None, ge=0)

    glasses_etc_qty: Optional[float] = Field(default=None, ge=0)
    glasses_etc_rate: Optional[float] = Field(default=None, ge=0)
    glasses_etc: Optional[float] = Field(default=None, ge=0)

    other_rentals_qty: Optional[float] = Field(default=None, ge=0)
    other_rentals_rate: Optional[float] = Field(default=None, ge=0)
    other_rentals: Optional[float] = Field(default=None, ge=0)

    total_c2: Optional[float] = Field(default=None, ge=0)
    total_c3: Optional[float] = Field(default=None, ge=0)
    total_costs: Optional[float] = Field(default=None, ge=0)
    gross_profit: Optional[float] = None
    gross_margin_pct: Optional[float] = None

    notes: Optional[str] = None
    status: Optional[str] = None


class CateringQuotationResponse(BaseModel):
    id: str
    name: str
    service_address: str
    service_date: str
    service_time: Optional[str] = None
    quotation_no: str
    prepared_date: str
    prepared_by: str

    estimated_pax: int
    food_cost_per_pax: float
    std_margin_per_pax: float
    quoted_price_per_pax: float
    approved_by: Optional[str] = None

    revenue_notes: Optional[str] = None
    menu_file_url: Optional[str] = None
    menu_file_name: Optional[str] = None

    revenue_qty: float = 0
    revenue_rate: float = 0
    total_revenue: float = 0

    food_cost_qty: float = 0
    food_cost_rate: float = 0
    food_cost: float = 0

    staff_cost_qty: float = 0
    staff_cost_rate: float = 0
    staff_cost: float = 0

    full_day_service_qty: float = 0
    full_day_service_rate: float = 0
    full_day_service: float = 0

    half_day_service_qty: float = 0
    half_day_service_rate: float = 0
    half_day_service: float = 0

    outsourced_service_qty: float = 0
    outsourced_service_rate: float = 0
    outsourced_service: float = 0

    transport_qty: float = 0
    transport_rate: float = 0
    transport: float = 0

    decoration_qty: float = 0
    decoration_rate: float = 0
    decoration: float = 0

    glasses_etc_qty: float = 0
    glasses_etc_rate: float = 0
    glasses_etc: float = 0

    other_rentals_qty: float = 0
    other_rentals_rate: float = 0
    other_rentals: float = 0

    total_c2: float = 0
    total_c3: float = 0
    total_costs: float = 0
    gross_profit: float = 0
    gross_margin_pct: float = 0
    status: str = "Pending"

    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class PaginatedCateringQuotationResponse(BaseModel):
    total_results: int
    page: int
    total_pages: int
    limit: int
    data: List[CateringQuotationResponse]