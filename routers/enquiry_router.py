from typing import List

from fastapi import APIRouter, Depends, status, Query
from auth.dependencies import get_current_user
from db.database import get_db
from models.enquiry_model import EnquiryCreate, EnquiryResponse, EnquiryUpdate, PaginatedEnquiryResponse
from models.base_model import StandardResponse
from controller.enquiry_controller import EnquiryController

router = APIRouter(prefix="/enquiries", tags=["Enquiries"])


@router.post(
    "/",
    response_model=StandardResponse[EnquiryResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new enquiry",
)
async def create_enquiry(
    data: EnquiryCreate,
    db=Depends(get_db),
):
    """Create a new enquiry."""
    result = await EnquiryController.create_enquiry(data, db)
    return StandardResponse(
        status_code=status.HTTP_201_CREATED,
        message="Enquiry Created Successfully",
        result_data=result,
    )


@router.get(
    "/",
    response_model=StandardResponse[PaginatedEnquiryResponse],
    summary="Get all enquiries with pagination",
)
async def get_all_enquiries_paginated(
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=10, ge=1, le=100, description="Items per page"),
    db=Depends(get_db),
    _: dict = Depends(get_current_user),                
):
    """Return a paginated list of enquiries."""
    result = await EnquiryController.get_all_enquiries_paginated(db, page, limit)
    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="Enquiries Fetched Successfully",
        result_data=result,
    )


@router.get(
    "/fetch_all",
    response_model=StandardResponse[List[EnquiryResponse]],
    summary="Get all enquiries",
)
async def get_all_enquiries(
    db=Depends(get_db),              
):
    """Return a list of enquiries."""
    result = await EnquiryController.get_all_enquiries(db)
    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="Enquiries Fetched Successfully",
        result_data=result,
    )


@router.get(
    "/{enquiry_id}",
    response_model=StandardResponse[EnquiryResponse],
    summary="Get a single enquiry by ID",
)
async def get_enquiry(
    enquiry_id: str,
    db=Depends(get_db),
    _: dict = Depends(get_current_user),                
):
    """Fetch one enquiry by its ID."""
    result = await EnquiryController.get_enquiry(enquiry_id, db)
    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="Enquiry Fetched Successfully",
        result_data=result,
    )


@router.patch(
    "/{enquiry_id}",
    response_model=StandardResponse[EnquiryResponse],
    summary="Partially update an enquiry",
)
async def update_enquiry(
    enquiry_id: str,
    data: EnquiryUpdate,
    db=Depends(get_db),
    
):
    """Update one or more fields of an enquiry."""
    result = await EnquiryController.update_enquiry(enquiry_id, data, db)
    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="Enquiry Updated Successfully",
        result_data=result,
    )


@router.delete(
    "/{enquiry_id}",
    response_model=StandardResponse[dict],
    summary="Delete an enquiry",
)
async def delete_enquiry(
    enquiry_id: str,
    db=Depends(get_db),
    _: dict = Depends(get_current_user),                
):
    """Hard-delete an enquiry."""
    result = await EnquiryController.delete_enquiry(enquiry_id, db)
    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="Enquiry Deleted Successfully",
        result_data=result,
    )