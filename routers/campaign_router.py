import io
import json
import os
import uuid
import csv
from typing import Optional
from fastapi import (APIRouter,Depends,File,Form,UploadFile,Request,HTTPException,status,Query)
import pandas as pd
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
    if filename.endswith(".csv"):
        text = file_bytes.decode("utf-8", errors="ignore")
        reader = csv.DictReader(io.StringIO(text))

        return [
            {
                "name": (r.get("name") or "").strip(),
                "country_code": (r.get("country_code") or "").strip(),
                "phone_number": (r.get("phone_number") or "").strip(),
            }
            for r in reader
            if r.get("phone_number")
        ]

    elif filename.endswith((".xlsx", ".xls")):
        df = pd.read_excel(io.BytesIO(file_bytes))
        df = df.where(pd.notna(df), None)

        customers = []

        for _, row in df.iterrows():
            phone = str(row.get("phone_number", "") or "").strip()

            if not phone:
                continue

            customers.append({
                "name": str(row.get("name", "") or "").strip(),
                "country_code": str(row.get("country_code", "") or "").strip(),
                "phone_number": phone,
            })

        return customers

    else:
        raise HTTPException(
            status_code=400,
            detail="Only CSV, XLSX, XLS files are supported"
        )


@router.post(
    "/",
    response_model=StandardResponse[CampaignResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_campaign(
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    campaign_image: Optional[UploadFile] = File(None),
    customers_file: Optional[UploadFile] = File(None),
    customers: Optional[str] = Form(None),
    db=Depends(get_db),
):
    final_customers = []

    if customers_file and customers_file.filename:
        file_bytes = await customers_file.read()
        final_customers.extend(parse_file(file_bytes, customers_file.filename))

    if customers:
        try:
            parsed = json.loads(customers)
            for c in parsed:
                final_customers.append({
                    "name": c.get("name", ""),
                    "country_code": c.get("country_code", ""),
                    "phone_number": c.get("phone_number", ""),
                })
        except Exception:
            raise HTTPException(400, "Invalid customers JSON")

    if not final_customers:
        raise HTTPException(400, "No customers provided")

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
        message="Campaign created successfully",
        result_data=result,
    )


@router.get(
    "/fetch_all",
    response_model=StandardResponse[list[CampaignResponse]]
)
async def get_all_campaigns(db=Depends(get_db)):

    result = await CampaignController.get_all_campaigns(db)

    return StandardResponse(
        status_code=200,
        message="Campaigns fetched successfully",
        result_data=result
    )


@router.get(
    "/",
    response_model=StandardResponse[PaginatedCampaignResponse]
)
async def get_paginated_campaigns(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=1000),
    db=Depends(get_db),
):

    result = await CampaignController.get_paginated_campaigns(db, page, limit)

    return StandardResponse(
        status_code=200,
        message="Paginated campaigns fetched successfully",
        result_data=result
    )


@router.get("/{campaign_id}", response_model=StandardResponse[CampaignResponse])
async def get_campaign(campaign_id: str, db=Depends(get_db)):

    result = await CampaignController.get_one_campaign(campaign_id, db)

    return StandardResponse(
        status_code=200,
        message="Campaign fetched successfully",
        result_data=result
    )


@router.put("/{campaign_id}", response_model=StandardResponse[CampaignResponse])
async def update_campaign(
    campaign_id: str,
    data: CampaignUpdate,
    db=Depends(get_db),
):

    result = await CampaignController.update_campaign(db, campaign_id, data)

    return StandardResponse(
        status_code=200,
        message="Campaign updated successfully",
        result_data=result
    )


@router.delete("/{campaign_id}")
async def delete_campaign(campaign_id: str, db=Depends(get_db)):

    result = await CampaignController.remove_campaign(campaign_id, db)

    return StandardResponse(
        status_code=200,
        message="Campaign deleted successfully",
        result_data=result
    )