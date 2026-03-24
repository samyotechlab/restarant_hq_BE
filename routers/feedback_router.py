from typing import List
from fastapi import APIRouter, Depends, status, Query
from db.database import get_db
from models.feedback_model import (
    FeedbackCreate,
    FeedbackResponse,
    FeedbackUpdate,
    PaginatedFeedbackResponse,
)
from models.base_model import StandardResponse
from controller.feedback_controller import FeedbackController

router = APIRouter(prefix="/feedback", tags=["Feedback"])


@router.post(
    "/",
    response_model=StandardResponse[FeedbackResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new feedback",
)
async def create_feedback(
    data: FeedbackCreate,
    db=Depends(get_db),
    
):
    """Submit new feedback. No authentication required."""
    result = await FeedbackController.create_feedback(data, db)
    return StandardResponse(
        status_code=status.HTTP_201_CREATED,
        message="Feedback Submitted Successfully",
        result_data=result,
    )


@router.get(
    "/fetch_all",
    response_model=StandardResponse[List[FeedbackResponse]],
    summary="Get all feedback unpaginated",
)
async def fetch_all_feedback(
    db=Depends(get_db),
    
):
    """Return all feedback without pagination. No authentication required."""
    result = await FeedbackController.fetch_all_feedback(db)
    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="Feedback Fetched Successfully",
        result_data=result,
    )


@router.get(
    "/",
    response_model=StandardResponse[PaginatedFeedbackResponse],
    summary="Get all feedback with pagination",
)
async def get_paginated_feedback(
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=10, ge=1, le=100, description="Items per page"),
    db=Depends(get_db),
    
):
    """Return a paginated list of feedback. No authentication required."""
    result = await FeedbackController.get_paginated_feedback(db, page, limit)
    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="Feedback Fetched Successfully",
        result_data=result,
    )


@router.get(
    "/{feedback_id}",
    response_model=StandardResponse[FeedbackResponse],
    summary="Get a single feedback by ID",
)
async def get_feedback(
    feedback_id: str,
    db=Depends(get_db),
    # no auth
):
    """Fetch one feedback by its ID."""
    result = await FeedbackController.get_feedback(feedback_id, db)
    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="Feedback Fetched Successfully",
        result_data=result,
    )


@router.patch(
    "/{feedback_id}",
    response_model=StandardResponse[FeedbackResponse],
    summary="Partially update a feedback",
)
async def update_feedback(
    feedback_id: str,
    data: FeedbackUpdate,
    db=Depends(get_db),
    
):
    """Update one or more fields of a feedback entry."""
    result = await FeedbackController.update_feedback(feedback_id, data, db)
    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="Feedback Updated Successfully",
        result_data=result,
    )


@router.delete(
    "/{feedback_id}",
    response_model=StandardResponse[dict],
    summary="Delete a feedback",
)
async def delete_feedback(
    feedback_id: str,
    db=Depends(get_db),
    # no auth
):
    """Hard-delete a feedback entry."""
    result = await FeedbackController.delete_feedback(feedback_id, db)
    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="Feedback Deleted Successfully",
        result_data=result,
    )