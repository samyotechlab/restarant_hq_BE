from fastapi import APIRouter, Depends, Query, status
from auth.dependencies import get_current_user
from controller.upsell_item_controller import UpsellItemController
from db.database import get_db
from models.base_model import StandardResponse
from models.upsell_item_model import PaginatedUpsellItemResponse, UpsellItemCreate, UpsellItemResponse, UpsellItemUpdate


router = APIRouter(prefix='/upsell-items', tags=['Upsell Items'])

@router.post(
  '/',
  response_model=StandardResponse[UpsellItemResponse],
  status_code=status.HTTP_201_CREATED,
)
async def create_item(
   data: UpsellItemCreate, 
   db=Depends(get_db),
   _: dict = Depends(get_current_user),
):
  result = await UpsellItemController.create_upsell_item(data, db)
  return StandardResponse(
    status_code=status.HTTP_201_CREATED,
    message="Upselling Item Created",
    result_data=result
  )


@router.get(
    "/fetch_all",
    response_model=StandardResponse[list[UpsellItemResponse]],
    summary="Get all Upselling Items unpaginated",
)
async def fetch_all_item_offer(
    db=Depends(get_db),
    # no auth on fetch_all
):
    """Return all Upselling Items without pagination. No authentication required."""
    result = await UpsellItemController.get_all(db)
    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="Item Offers Fetched Successfully",
        result_data=result,
    )


@router.get(
  '/',
  response_model=StandardResponse[PaginatedUpsellItemResponse],
  status_code=status.HTTP_200_OK
)
async def get_paginated_offer(
  page: int = Query(default=1, ge=1, description="Page number"),
  limit: int = Query(default=10, ge=1, le=1000, description="Items per page"),
  db=Depends(get_db),
  _: dict = Depends(get_current_user),
):
  result = await UpsellItemController.get_all_upsell_item_paginated(db, page, limit)
  return StandardResponse(
    status_code=status.HTTP_200_OK,
    message="Upselling Items Fetched Successfully",
    result_data=result,
  )


@router.get(
    "/{offer_id}",
    response_model=StandardResponse[UpsellItemResponse],
    summary="Get a single upselling item by ID",
)
async def get_item_offer_id(
    offer_id: str,
    db=Depends(get_db),
    _: dict = Depends(get_current_user),                
):
    """Fetch one upselling item by its ID."""
    result = await UpsellItemController.get_item_by_id(offer_id, db)
    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="Upselling Item Fetched Successfully",
        result_data=result,
    )


@router.patch(
   '/{offer_id}',
   response_model=StandardResponse[UpsellItemResponse],
   summary="Update single upselling item by ID",
)
async def update_item_offer(
   offer_id: str,
   data: UpsellItemUpdate,
   db=Depends(get_db),
   _: dict = Depends(get_current_user),
):
   result = await UpsellItemController.update_upsell_item(offer_id, data, db)
   return StandardResponse(
      status_code=status.HTTP_200_OK,
      message="Upselling Item Updated",
      result_data=result
   )


@router.delete(
    "/{offer_id}",
    response_model=StandardResponse[dict],
    summary="Delete a upselling item",
)
async def delete_ticket(
    offer_id: str,
    db=Depends(get_db),
    _: dict = Depends(get_current_user),                
):
    """Hard-delete a upselling item."""
    result = await UpsellItemController.remove_upsell_item(offer_id, db)
    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="Upselling Item Deleted Successfully",
        result_data=result,
    )