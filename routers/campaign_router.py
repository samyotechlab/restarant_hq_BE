from typing import List
from fastapi import APIRouter, Depends, status, Query
from auth.dependencies import get_current_user
from db.database import get_db
from models.campaign_model import (
    CampaignCreate,
    CampaignResponse,
    CampaignUpdate,
    PaginatedCampaignResponse,
)
from models.base_model import StandardResponse
from controller.campaign_controller import CampaignController

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])


@router.post(
    "/",
    response_model=StandardResponse[CampaignResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new marketing campaign",
)
async def create_campaign(
    data: CampaignCreate,
    db=Depends(get_db),
    _: dict = Depends(get_current_user),                
):
    """Create a new marketing campaign."""
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
)
async def fetch_all_campaigns(
    db=Depends(get_db),
    _: dict = Depends(get_current_user),                
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