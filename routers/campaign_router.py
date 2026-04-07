from datetime import datetime
import os
from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status, Query
from auth.dependencies import get_current_user
from db.database import get_db
from models.campaign_model import (
    CampaignCreate,
    CampaignResponse,
    CampaignStatus,
    CampaignType,
    CampaignUpdate,
    PaginatedCampaignResponse,
)
from models.base_model import StandardResponse
from controller.campaign_controller import CampaignController

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])

UPLOAD_DIR = "uploads/campaigns"
BASE_URL = "https://mygangour.samyotech.in/api"

@router.post(
    "/",
    response_model=StandardResponse[CampaignResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new marketing campaign",
    include_in_schema=False
)
async def create_campaign(
    campaign_name: Optional[str] = Form(None),
    campaign_type: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    campaign_status: Optional[str] = Form("scheduled"),
    start_date: Optional[str] = Form(None),
    end_date: Optional[str] = Form(None),
    offer_price: Optional[float] = Form(0.0),
    discount_percentage: Optional[float] = Form(0.0),
    menu_items: Optional[List[str]] = Form([]),
    image: Optional[UploadFile] = File(None),
    db=Depends(get_db),
    # _: dict = Depends(get_current_user),               
):
    """Create a new marketing campaign."""
    image_url = None
    if image and image.filename:
        allowed = ["image/jpeg", "image/png", "image/webp", "image/jpg"]
        if image.content_type not in allowed:
            raise HTTPException(status_code=400, detail="Only JPG, PNG, WEBP allowed")

        contents = await image.read()
        if len(contents) > 5 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Image must be under 5MB")

        os.makedirs(UPLOAD_DIR, exist_ok=True)
        ext = image.filename.split(".")[-1].lower()
        filename = f"{uuid.uuid4().hex}.{ext}"
        with open(f"{UPLOAD_DIR}/{filename}", "wb") as f:
            f.write(contents)
        image_url = f"{BASE_URL}/uploads/campaigns/{filename}"

    # Build CampaignCreate from form fields
    data = CampaignCreate(
        campaign_name=campaign_name,
        campaign_type=CampaignType(campaign_type) if campaign_type else None,
        description=description,
        status=CampaignStatus(campaign_status) if campaign_status else None,
        start_date=datetime.fromisoformat(start_date) if start_date else None,
        end_date=datetime.fromisoformat(end_date) if end_date else None,
        offer_price=offer_price,
        discount_percentage=discount_percentage,
        menu_items=menu_items,
        image_url=image_url,  # ← pass saved url
    )
    result = await CampaignController.create_campaign(data, db)
    return StandardResponse(
        status_code=status.HTTP_201_CREATED,
        message="Campaign Created Successfully",
        result_data=result,
    )


@router.get(
    "/fetch_all",
    response_model=StandardResponse[List[CampaignResponse]],
    summary="Get all campaigns unpaginated",
    include_in_schema=False
)
async def fetch_all_campaigns(
    db=Depends(get_db),
    # _: dict = Depends(get_current_user),               
):
    """Return all campaigns without pagination."""
    result = await CampaignController.get_all_campaigns(db)
    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="Campaigns Fetched Successfully",
        result_data=result,
    )


@router.get(
    "/",
    response_model=StandardResponse[PaginatedCampaignResponse],
    summary="Get all campaigns with pagination",
)
async def get_paginated_campaigns(
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=10, ge=1, le=100, description="Items per page"),
    db=Depends(get_db),
    _: dict = Depends(get_current_user),                
):
    """Return a paginated list of campaigns."""
    result = await CampaignController.get_paginated_campaigns(db, page, limit)
    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="Campaigns Fetched Successfully",
        result_data=result,
    )


@router.get(
    "/{campaign_id}",
    response_model=StandardResponse[CampaignResponse],
    summary="Get a single campaign by ID",
)
async def get_campaign(
    campaign_id: str,
    db=Depends(get_db),
    _: dict = Depends(get_current_user),               
):
    """Fetch one campaign by its ID — menu items are populated."""
    result = await CampaignController.get_campaign(campaign_id, db)
    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="Campaign Fetched Successfully",
        result_data=result,
    )


@router.patch(
    "/{campaign_id}",
    response_model=StandardResponse[CampaignResponse],
    summary="Partially update a campaign",
)
async def update_campaign(
    campaign_id: str,
    data: CampaignUpdate,
    db=Depends(get_db),
    _: dict = Depends(get_current_user),                
):
    """Update one or more fields of a campaign."""
    result = await CampaignController.update_campaign(campaign_id, data, db)
    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="Campaign Updated Successfully",
        result_data=result,
    )


@router.delete(
    "/{campaign_id}",
    response_model=StandardResponse[dict],
    summary="Delete a campaign",
)
async def delete_campaign(
    campaign_id: str,
    db=Depends(get_db),
    _: dict = Depends(get_current_user),                
):
    """Hard-delete a campaign."""
    result = await CampaignController.delete_campaign(campaign_id, db)
    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="Campaign Deleted Successfully",
        result_data=result,
    )