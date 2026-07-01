import io
import json
import os
import uuid
import csv
from datetime import datetime, timezone
from typing import Optional
from fastapi import (APIRouter,Depends,File,Form,UploadFile,Request,HTTPException,status,Query)
import pandas as pd
from auth.dependencies import get_current_user
from controller.campaign_controller import CampaignController
from db.database import get_db
from models.base_model import StandardResponse
from models.campaign_model import (
    CampaignCreate,
    CampaignResponse,
    CampaignUpdate,
    Customer,
    PaginatedCampaignResponse,
)

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])

UPLOAD_DIR = "uploads/campaigns"

def parse_file(file_bytes: bytes, filename: str):
    filename = filename.lower()

    def pick(row: dict, *keys):
        normalized = [k.strip().lower() for k in keys]
        for rk, rv in row.items():
            col = rk.strip().lower()
            if col in normalized:
                v = str(rv or "").strip()
                if v:
                    return v
        return ""

    def normalize_row(row: dict) -> dict | None:
        phone = pick(row, "phone", "phone_number", "mobile", "contact")
        phone = (
            phone.replace(" ", "")
            .replace("-", "")
            .replace("(", "")
            .replace(")", "")
        )
        if not phone:
            return None

        country_code = pick(row, "country_code", "code", "country code")
        if not country_code:
            digits = "".join(ch for ch in phone if ch.isdigit())
            if len(digits) == 10:
                country_code = "+91"
            elif len(digits) == 9:
                country_code = "+971"
            elif len(digits) == 11:
                country_code = "+86"
            else:
                country_code = "+971"

        address = pick(row, "primary address", "address", "primary_address")

        return {
            "name": pick(row, "name", "customer name", "full name") or "Unknown",
            "country_code": country_code,
            "phone_number": phone,
            "status": "Pending",
            "address": address,
        }

    if filename.endswith(".csv"):
        text = file_bytes.decode("utf-8", errors="ignore")
        f = io.StringIO(text)
        for _ in range(4):
            next(f, None)

        reader = csv.DictReader(f)
        rows: list[dict] = []
        for row in reader:
            norm = normalize_row(row)
            if norm is not None:
                rows.append(norm)
        return rows

    # Excel
    elif filename.endswith((".xlsx", ".xls")):
        # Header is row 5 → zero-based index 4
        df = pd.read_excel(io.BytesIO(file_bytes), header=4)
        df = df.where(pd.notna(df), None)
        rows: list[dict] = []
        for _, row in df.iterrows():
            norm = normalize_row(dict(row))
            if norm is not None:
                rows.append(norm)
        return rows

    else:
        raise HTTPException(
            status_code=400,
            detail="Only CSV, XLSX, XLS files are supported",
        )


@router.post(
    "/",
    response_model=StandardResponse[CampaignResponse],
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def create_campaign(
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    campaign_image: Optional[UploadFile] = File(None),
    customers_file: Optional[UploadFile] = File(None),
    customers: Optional[str] = Form(None),
    offset: int = Form(0),
    batch_size: int = Form(1000),
    db=Depends(get_db),
    _: dict = Depends(get_current_user),
):
    final_customers: list[dict] = []

    if customers:
        try:
            parsed = json.loads(customers)
            for c in parsed:
                final_customers.append({
                    "name": c.get("name", ""),
                    "country_code": c.get("country_code", ""),
                    "phone_number": c.get("phone_number", ""),
                    "status": c.get("status", ""),
                })
        except Exception:
            raise HTTPException(400, "Invalid customers JSON")

    file_customers: list[dict] = []

    if customers_file and customers_file.filename:
        file_bytes = await customers_file.read()
        parsed_file_customers = parse_file(file_bytes, customers_file.filename)

        file_customers = parsed_file_customers[offset: offset + batch_size]

    final_customers.extend(file_customers)

    if not final_customers:
        raise HTTPException(400, "No customers to add from file or manual selection")

    if file_customers:
        now = datetime.now(timezone.utc)
        for cust in file_customers:
            await db["customers"].update_one(
                {"phone_number": cust["phone_number"]},
                {
                    "$setOnInsert": {
                        "name": cust["name"],
                        "country_code": cust["country_code"],
                        "phone_number": cust["phone_number"],
                        "address": cust.get("address"),
                        "created_at": now,
                        "from_where": "campaign_bulk_upload",
                    }
                },
                upsert=True,
            )

    image_url = None
    if campaign_image and campaign_image.filename:
        allowed = ["image/jpeg", "image/png", "image/webp", "image/jpg"]
        if campaign_image.content_type not in allowed:
            raise HTTPException(400, "Only image files allowed")

        contents = await campaign_image.read()
        if len(contents) > 5 * 1024 * 1024:
            raise HTTPException(400, "Image must be under 5MB")

        os.makedirs(UPLOAD_DIR, exist_ok=True)
        ext = campaign_image.filename.split(".")[-1]
        filename = f"{uuid.uuid4().hex}.{ext}"
        filepath = f"{UPLOAD_DIR}/{filename}"
        with open(filepath, "wb") as f:
            f.write(contents)

        base_url = str(request.base_url).rstrip("/")
        image_url = f"{base_url}/{filepath}"

    data = CampaignCreate(
        title=title,
        description=description,
        customers=[Customer(**c) for c in final_customers],
    )
    result = await CampaignController.create_campaign(data, db, image_url)

    return StandardResponse(
        status_code=201,
        message=(
            f"Campaign created successfully with {len(final_customers)} customers "
            f"({len(file_customers)} from sheet, {len(final_customers) - len(file_customers)} manual)"
        ),
        result_data=result,
    )


@router.post(
    "/preview",
    response_model=StandardResponse[dict],
)
async def preview_campaign_file(
    customers_file: UploadFile = File(...),
    offset: int = Form(0),
    batch_size: int = Form(1000),
    db=Depends(get_db),
    _: dict = Depends(get_current_user),
):
    if not customers_file.filename:
        raise HTTPException(400, "No file provided")

    file_bytes = await customers_file.read()
    parsed_file_customers = parse_file(file_bytes, customers_file.filename)
    total_parsed = len(parsed_file_customers)

    eligible_customers = parsed_file_customers
    skipped_existing: list[dict] = []

    window_customers = eligible_customers[offset: offset + batch_size]
    window_count = len(window_customers)
    remaining_count = max(0, len(eligible_customers) - (offset + window_count))

    return StandardResponse(
        status_code=200,
        message="Preview calculated",
        result_data={
            "total_rows": total_parsed,
            "eligible_total": len(eligible_customers),
            "window_count": window_count,
            "skipped_existing_count": len(skipped_existing),
            "remaining_count": remaining_count,
            "sample_window": window_customers[:20],
            "sample_skipped": skipped_existing[:20],
        },
    )


@router.get(
    "/fetch_all",
    response_model=StandardResponse[list[CampaignResponse]],
    include_in_schema=False,
)
async def get_all_campaigns(db=Depends(get_db)):
    result = await CampaignController.get_all_campaigns(db)
    return StandardResponse(
        status_code=200,
        message="Campaigns fetched successfully",
        result_data=result,
    )


@router.get(
    "/",
    response_model=StandardResponse[PaginatedCampaignResponse],
)
async def get_paginated_campaigns(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=1000),
    db=Depends(get_db),
    _: dict = Depends(get_current_user),
):
    result = await CampaignController.get_paginated_campaigns(db, page, limit)
    return StandardResponse(
        status_code=200,
        message="Paginated campaigns fetched successfully",
        result_data=result,
    )


@router.get(
    "/{campaign_id}",
    response_model=StandardResponse[CampaignResponse],
    include_in_schema=False,
)
async def get_campaign(campaign_id: str, db=Depends(get_db)):
    result = await CampaignController.get_one_campaign(campaign_id, db)
    return StandardResponse(
        status_code=200,
        message="Campaign fetched successfully",
        result_data=result,
    )


@router.patch(
    "/{campaign_id}",
    response_model=StandardResponse[CampaignResponse],
)
async def update_campaign(
    campaign_id: str,
    data: CampaignUpdate,
    db=Depends(get_db),
    _: dict = Depends(get_current_user),
):
    result = await CampaignController.update_campaign(db, campaign_id, data)
    return StandardResponse(
        status_code=200,
        message="Campaign updated successfully",
        result_data=result,
    )


@router.patch(
    "/{campaign_id}/customer-status",
    include_in_schema=False,
)
async def update_customer_status(
    campaign_id: str,
    phone_number: str,
    status: str = Form(...),
    fail_reason: Optional[str] = Form(None),
    db=Depends(get_db),
):
    normalized = status.strip().lower()
    if normalized == "error":
        normalized = "ecosystem-error"

    await CampaignController.update_customer_status(
        db=db,
        campaign_id=campaign_id,
        phone_number=phone_number,
        new_status=normalized,
        fail_reason=fail_reason,
    )

    return {"message": "Customer status updated"}


@router.delete(
    "/{campaign_id}/customers/{phone_number}",
    response_model=StandardResponse[CampaignResponse],
    include_in_schema=False,
)
async def remove_customer_from_campaign(
    campaign_id: str,
    phone_number: str,
    db=Depends(get_db),
    _: dict = Depends(get_current_user),
):
    result = await CampaignController.remove_customer(db, campaign_id, phone_number)
    return StandardResponse(
        status_code=200,
        message="Customer removed from campaign successfully",
        result_data=result,
    )


@router.delete("/{campaign_id}")
async def delete_campaign(
    campaign_id: str,
    db=Depends(get_db),
    _: dict = Depends(get_current_user),
):
    result = await CampaignController.remove_campaign(campaign_id, db)
    return StandardResponse(
        status_code=200,
        message="Campaign deleted successfully",
        result_data=result,
    )


@router.get(
    "/used-phones",
    response_model=StandardResponse[list[str]],
    include_in_schema=False,
)
async def used_phones(
    db=Depends(get_db),
    _: dict = Depends(get_current_user),
):
    phones = await CampaignController.get_all_used_phones(db)
    return StandardResponse(
        status_code=200,
        message="Used Phones fetched",
        result_data=phones,
    )