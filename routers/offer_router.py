from datetime import datetime
import os
from typing import List, Optional
from urllib.parse import urlparse
import uuid
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status, Query
from auth.dependencies import get_current_user
from db.database import get_db
from models.offers_model import (
    OfferCreate,
    OfferResponse,
    OfferStatus,
    OfferType,
    OfferUpdate,
    PaginatedOfferResponse,
)
from models.base_model import StandardResponse
from controller.offer_controller import OfferController

router = APIRouter(prefix="/offers", tags=["Offers"])

UPLOAD_DIR = "uploads/offers"

@router.post(
    "/",
    response_model=StandardResponse[OfferResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new marketing offer",
    include_in_schema=False
)
async def create_offer(
    request: Request,
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
    """Create a new marketing offer."""
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
        base_url = str(request.base_url).rstrip("/")
        image_url = f"{base_url}/uploads/offers/{filename}"

    # Build CampaignCreate from form fields
    data = OfferCreate(
        campaign_name=campaign_name,
        campaign_type=OfferType(campaign_type) if campaign_type else None,
        description=description,
        status=OfferStatus(campaign_status) if campaign_status else None,
        start_date=datetime.fromisoformat(start_date) if start_date else None,
        end_date=datetime.fromisoformat(end_date) if end_date else None,
        offer_price=offer_price,
        discount_percentage=discount_percentage,
        menu_items=menu_items,
        image_url=image_url,  # ← pass saved url
    )
    result = await OfferController.create_offer(data, db)
    return StandardResponse(
        status_code=status.HTTP_201_CREATED,
        message="Offer Created Successfully",
        result_data=result,
    )


@router.get(
    "/fetch_all",
    response_model=StandardResponse[List[OfferResponse]],
    summary="Get all offers unpaginated",
    include_in_schema=False
)
async def fetch_all_offer(
    db=Depends(get_db),
    # _: dict = Depends(get_current_user),               
):
    """Return all offers without pagination."""
    result = await OfferController.get_all_offers(db)
    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="Offers Fetched Successfully",
        result_data=result,
    )


@router.get(
    "/",
    response_model=StandardResponse[PaginatedOfferResponse],
    summary="Get all offers with pagination",
)
async def get_paginated_offer(
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=10, ge=1, le=100, description="Items per page"),
    db=Depends(get_db),
    _: dict = Depends(get_current_user),                
):
    """Return a paginated list of offers."""
    result = await OfferController.get_paginated_offers(db, page, limit)
    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="Offers Fetched Successfully",
        result_data=result,
    )


@router.get(
    "/{offer_id}",
    response_model=StandardResponse[OfferResponse],
    summary="Get a single offer by ID",
)
async def get_offer(
    offer_id: str,
    db=Depends(get_db),
    _: dict = Depends(get_current_user),               
):
    """Fetch one offer by its ID — menu items are populated."""
    result = await OfferController.get_offer(offer_id, db)
    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="Offer Fetched Successfully",
        result_data=result,
    )


@router.patch(
    "/{campaign_id}",
    response_model=StandardResponse[OfferResponse],
    summary="Partially update a offer",
)
async def update_offer(
    campaign_id: str,
    request: Request,
    campaign_name: Optional[str] = Form(None),
    campaign_type: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    campaign_status: Optional[str] = Form(None),
    start_date: Optional[str] = Form(None),
    end_date: Optional[str] = Form(None),
    offer_price: Optional[float] = Form(None),
    discount_percentage: Optional[float] = Form(None),
    menu_items: Optional[List[str]] = Form(None),
    image: Optional[UploadFile] = File(None),
    db=Depends(get_db),
    _: dict = Depends(get_current_user),
):
    existing = await OfferController.get_offer(campaign_id, db)

    if not existing:
        raise HTTPException(status_code=404, detail="Offer not found")

    image_url = existing.image_url

    # 👉 If new image uploaded
    if image and image.filename:
        allowed = ["image/jpeg", "image/png", "image/webp", "image/jpg"]
        if image.content_type not in allowed:
            raise HTTPException(status_code=400, detail="Only JPG, PNG, WEBP allowed")

        contents = await image.read()
        if len(contents) > 5 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Image must be under 5MB")
        
        # 🔥 DELETE OLD IMAGE
        if existing.image_url:
            parsed = urlparse(existing.image_url)
            file_path = parsed.path.replace("/uploads/", "")
            full_path = os.path.join("uploads", file_path)

            if os.path.exists(full_path) and os.path.isfile(full_path):
                os.remove(full_path)

        # 🔥 SAVE NEW IMAGE
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        ext = image.filename.split(".")[-1].lower()
        filename = f"{uuid.uuid4().hex}.{ext}"

        with open(f"{UPLOAD_DIR}/{filename}", "wb") as f:
            f.write(contents)

        base_url = str(request.base_url).rstrip("/")
        image_url = f"{base_url}/uploads/offers/{filename}"

    # 🔥 Build update object
    data = OfferUpdate(
        campaign_name=campaign_name,
        campaign_type=OfferType(campaign_type) if campaign_type else None,
        description=description,
        status=OfferStatus(campaign_status) if campaign_status else None,
        start_date=datetime.fromisoformat(start_date) if start_date else None,
        end_date=datetime.fromisoformat(end_date) if end_date else None,
        offer_price=offer_price,
        discount_percentage=discount_percentage,
        menu_items=menu_items,
        image_url=image_url,
    )

    result = await OfferController.update_offer(campaign_id, data, db)

    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="Offer Updated Successfully",
        result_data=result,
    )


@router.delete(
    "/{offer_id}",
    response_model=StandardResponse[dict],
    summary="Delete a offer",
)
async def delete_offer(
    offer_id: str,
    db=Depends(get_db),
    _: dict = Depends(get_current_user),
):
    existing = await OfferController.get_offer(offer_id, db)

    if not existing:
        raise HTTPException(status_code=404, detail="Offer not found")

    # 🔥 DELETE IMAGE FROM DISK
    if existing.image_url:
        parsed = urlparse(existing.image_url)
        file_path = parsed.path.replace("/uploads/", "")
        full_path = os.path.join("uploads", file_path)

        if os.path.exists(full_path) and os.path.isfile(full_path):
            os.remove(full_path)

    # 🔥 DELETE FROM DB
    await OfferController.delete_offer(offer_id, db)

    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="Offer Deleted Successfully",
        result_data={},
    )