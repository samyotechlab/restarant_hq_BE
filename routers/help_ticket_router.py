from typing import List
from fastapi import APIRouter, Depends, status, Query
from auth.dependencies import get_current_user
from db.database import get_db
from models.help_ticket_model import (
    HelpTicketCreate,
    HelpTicketResponse,
    HelpTicketUpdate,
    PaginatedHelpTicketResponse,
)
from models.base_model import StandardResponse
from controller.help_ticket_controller import HelpTicketController

router = APIRouter(prefix="/help-tickets", tags=["Help Tickets"])


@router.post(
    "/",
    response_model=StandardResponse[HelpTicketResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new help ticket",
    include_in_schema=False
)
async def create_ticket(
    data: HelpTicketCreate,
    db=Depends(get_db),
    # no auth on create
):
    """Create a new help ticket. No authentication required."""
    result = await HelpTicketController.create_ticket(data, db)
    return StandardResponse(
        status_code=status.HTTP_201_CREATED,
        message="Help Ticket Created Successfully",
        result_data=result,
    )


@router.get(
    "/fetch_all",
    response_model=StandardResponse[List[HelpTicketResponse]],
    summary="Get all help tickets unpaginated",
    include_in_schema=False
)
async def fetch_all_tickets(
    db=Depends(get_db),
    # no auth on fetch_all
):
    """Return all help tickets without pagination. No authentication required."""
    result = await HelpTicketController.fetch_all_tickets(db)
    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="Help Tickets Fetched Successfully",
        result_data=result,
    )


@router.get(
    "/",
    response_model=StandardResponse[PaginatedHelpTicketResponse],
    summary="Get all help tickets with pagination",
)
async def get_paginated_tickets(
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=10, ge=1, le=100, description="Items per page"),
    db=Depends(get_db),
    _: dict = Depends(get_current_user),                
):
    """Return a paginated list of help tickets."""
    result = await HelpTicketController.get_paginated_tickets(db, page, limit)
    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="Help Tickets Fetched Successfully",
        result_data=result,
    )


@router.get(
    "/{ticket_id}",
    response_model=StandardResponse[HelpTicketResponse],
    summary="Get a single help ticket by ID",
)
async def get_ticket(
    ticket_id: str,
    db=Depends(get_db),
    _: dict = Depends(get_current_user),                
):
    """Fetch one help ticket by its ID — customer is populated."""
    result = await HelpTicketController.get_ticket(ticket_id, db)
    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="Help Ticket Fetched Successfully",
        result_data=result,
    )


@router.patch(
    "/{ticket_id}",
    response_model=StandardResponse[HelpTicketResponse],
    summary="Partially update a help ticket",
)
async def update_ticket(
    ticket_id: str,
    data: HelpTicketUpdate,
    db=Depends(get_db),
    _: dict = Depends(get_current_user),               
):
    """Update one or more fields of a help ticket."""
    result = await HelpTicketController.update_ticket(ticket_id, data, db)
    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="Help Ticket Updated Successfully",
        result_data=result,
    )


@router.delete(
    "/{ticket_id}",
    response_model=StandardResponse[dict],
    summary="Delete a help ticket",
)
async def delete_ticket(
    ticket_id: str,
    db=Depends(get_db),
    _: dict = Depends(get_current_user),                
):
    """Hard-delete a help ticket."""
    result = await HelpTicketController.delete_ticket(ticket_id, db)
    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="Help Ticket Deleted Successfully",
        result_data=result,
    )