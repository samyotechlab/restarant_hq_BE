from datetime import datetime
from enum import Enum
import json
from typing import List, Optional, Union
from pydantic import BaseModel, Field, field_validator


class OrderStatus(str, Enum):
    PENDING = "Pending"
    SUCCESS = "Success"
    FAILED  = "Failed"


class BulkJobStatus(str, Enum):
    QUEUED     = "queued"
    PROCESSING = "processing"
    COMPLETED  = "completed"
    FAILED     = "failed"


# ─────────────────────────────────────────────────────────────────────────────
# SUB-MODELS — used inside order documents
# ─────────────────────────────────────────────────────────────────────────────

class OrderItem(BaseModel):
    """
    A single item inside an order (used in create/update by frontend).
    menu_item → MongoDB ObjectId of the menu item as string.
    """
    menu_item:   str
    price:       Optional[float] = None
    quantity:    Optional[int]   = Field(None, gt=0)
    sub_total:   Optional[float] = None
    final_total: Optional[float] = None


class OrderItemBulk(BaseModel):
    """
    A single item inside a bulk-uploaded order.
    Carries ALL columns from the Excel sheet per row.
    menu_item → resolved ObjectId from menu_items (None if not found).
    """
    menu_item:   Optional[str]   = None
    item_name:   Optional[str]   = None
    variation:   Optional[str]   = None
    category:    Optional[str]   = None
    group_name:  Optional[str]   = None
    hsn:         Optional[str]   = None
    price:       Optional[float] = None
    quantity:    Optional[float] = None
    sub_total:   Optional[float] = None
    discount:    Optional[float] = None
    tax:         Optional[float] = None
    vat_rate:    Optional[float] = None
    vat_amount:  Optional[float] = None
    non_taxable: Optional[bool]  = False
    final_total: Optional[float] = None


# ─────────────────────────────────────────────────────────────────────────────
# POPULATED RESPONSE SUB-MODELS
# ─────────────────────────────────────────────────────────────────────────────

class OrderItemResponse(BaseModel):
    """
    A single item inside an order response.
    menu_item is populated from menu_items collection.
    Carries all fields stored during bulk upload + populated menu fields.
    """
    menu_item_id:  Optional[str]   = None
    item_no:       Optional[str]   = None
    item_name:     Optional[str]   = None
    image:         Optional[str]   = None
    category:      Optional[str]   = None
    base_price:    Optional[float] = None
    online_price:  Optional[float] = None
    dietary:       Optional[str]   = None
    available:     Optional[bool]  = None

    price:         Optional[float] = None   # actual charged price
    quantity:      Optional[float] = None
    sub_total:     Optional[float] = None
    final_total:   Optional[float] = None


class PopulatedCustomer(BaseModel):
    """Customer details embedded in order response."""
    customer_id:  Optional[str] = None
    name:         Optional[str] = None
    country_code: Optional[str] = None
    phone_number: Optional[str] = None
    address:      Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# ORDER CREATE / UPDATE (frontend use)
# ─────────────────────────────────────────────────────────────────────────────

class OrderCreate(BaseModel):
    """All fields optional — frontend handles required validation."""
    customer:       Optional[str]             = None
    items:          Optional[List[OrderItem]]
    @field_validator("items", mode="before")
    @classmethod
    def normalize_items(cls, v):
        if v is None or v == "":
            return []

        if isinstance(v, str):
            try:
                v = json.loads(v)
            except Exception:
                raise ValueError("items must be valid JSON array string")
        if isinstance(v, list):
            return v

        raise ValueError("Invalid items format")
    order_date: Optional[datetime] = None
    order_type: Optional[str] = None
    area: Optional[str] = None
    table_no: Optional[str] = None
    covers: Optional[float] = None
    server_name: Optional[str] = None
    assign_to: Optional[str] = None
    invoice_no: Optional[str] = None
    status:         OrderStatus     = Field(default=OrderStatus.PENDING)
    sub_total:      Optional[float]           = None
    tax:            Optional[float]           = None
    discount:       Optional[float]           = None
    grand_total:    Optional[float]           = None
    notes:          Optional[str]             = None
    payment_method: Optional[str] = Field(default="Pending")
    is_paid:        Optional[bool]            = Field(default=False)


class OrderUpdate(BaseModel):
    """All fields optional — supports partial updates."""
    customer:       Optional[str]             = None
    items:          Optional[List[OrderItem]] = None
    order_date: Optional[datetime] = None
    order_type: Optional[str] = None
    area: Optional[str] = None
    table_no: Optional[str] = None
    covers: Optional[float] = None
    server_name: Optional[str] = None
    assign_to: Optional[str] = None
    status:         Optional[OrderStatus]     = None
    sub_total:      Optional[float]           = None
    tax:            Optional[float]           = None
    discount:       Optional[float]           = None
    grand_total:    Optional[float]           = None
    notes:          Optional[str]             = None
    payment_method: Optional[str]   = None
    is_paid:        Optional[bool]            = None


# ─────────────────────────────────────────────────────────────────────────────
# ORDER RESPONSE (what API returns to frontend/n8n)
# ─────────────────────────────────────────────────────────────────────────────

class OrderResponse(BaseModel):
    """
    Full order document returned to client.
    customer and items are populated.
    Includes ALL sheet columns stored during bulk upload.
    """
    id:              str
    order_id:        str
    invoice_no:      Optional[str]   = None
    order_date:      Optional[datetime] = None
    order_timestamp: Optional[datetime] = None
    order_type:      Optional[str]   = None
    area:            Optional[str]   = None
    table_no:        Optional[str]   = None
    covers:          Optional[float] = None
    server_name:     Optional[str]   = None
    assign_to:       Optional[str]   = None
    customer:        Optional[PopulatedCustomer] = None
    items:           List[OrderItemResponse] = []
    sub_total:       Optional[float] = None
    discount:        Optional[float] = None
    tax:             Optional[float] = None
    grand_total:     Optional[float] = None
    vat_amount:      Optional[float] = None
    non_taxable:     Optional[float] = None
    gst:             Optional[str]   = None
    payment_method:  Optional[str] = None
    status:          OrderStatus
    is_paid:         bool
    notes:           Optional[str]  = None
    created_at:      datetime
    updated_at:      datetime


class PaginatedOrderResponse(BaseModel):
    """Wraps a page of orders with metadata for the frontend."""
    total_results: int
    page:          int
    limit:         int
    total_pages:   int
    data:          List[OrderResponse]


# ─────────────────────────────────────────────────────────────────────────────
# BULK UPLOAD JOB MODELS
# ─────────────────────────────────────────────────────────────────────────────

class ItemNotFound(BaseModel):
    """Represents a single item that could not be matched to menu_items."""
    invoice_no: str
    item_name:  str


class BulkUploadError(BaseModel):
    """Represents a processing error for a single invoice."""
    invoice_no: Optional[str] = None
    error:      str


class OrderBulkJobResponse(BaseModel):
    """
    Response shape for bulk order upload job status.
    Returned by GET /orders/bulk_upload_file/status/{job_id}
    """
    job_id:             str
    file_name:          str
    status:             BulkJobStatus
    total_invoices:     int
    processed_invoices: int
    progress_percent:   float
    customers_created:  int
    customers_found:    int
    orders_created:     int
    orders_skipped: int = 0
    skipped_no_phone:   int
    items_not_found:    List[ItemNotFound]  = []
    errors:             List[BulkUploadError] = []
    started_at:         Optional[datetime]  = None
    completed_at:       Optional[datetime]  = None
    created_at:         datetime