

from fastapi import APIRouter, Depends, Query, status

from auth.dependencies import get_current_user
from controller.item_offer_controller import ItemOfferController
from db.database import get_db
from models.base_model import StandardResponse
from models.item_offer_model import ItemOfferCreate, ItemOfferResponse, ItemOfferUpdate, PaginatedItemOfferResponse


router = APIRouter(prefix='/item-offer', tags=['Item Offers'])

@router.post(
  '/',
  response_model=StandardResponse[ItemOfferResponse],
  status_code=status.HTTP_201_CREATED,
)
async def create_item_offer(
   data: ItemOfferCreate, 
   db=Depends(get_db),
   _: dict = Depends(get_current_user),
):
  result = await ItemOfferController.createItemOffer(data, db)
  return StandardResponse(
    status_code=status.HTTP_201_CREATED,
    message="Item Offer Created",
    result_data=result
  )


@router.get(
    "/fetch_all",
    response_model=StandardResponse[list[ItemOfferResponse]],
    summary="Get all help tickets unpaginated",
)
async def fetch_all_item_offer(
    db=Depends(get_db),
    # no auth on fetch_all
):
    """Return all help tickets without pagination. No authentication required."""
    result = await ItemOfferController.get_all(db)
    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="Item Offers Fetched Successfully",
        result_data=result,
    )


@router.get(
  '/',
  response_model=StandardResponse[PaginatedItemOfferResponse],
  status_code=status.HTTP_200_OK
)
async def get_paginated_offer(
  page: int = Query(default=1, ge=1, description="Page number"),
  limit: int = Query(default=10, ge=1, le=100, description="Items per page"),
  db=Depends(get_db),
  _: dict = Depends(get_current_user),
):
  result = await ItemOfferController.get_all_item_offer_paginated(db, page, limit)
  return StandardResponse(
    status_code=status.HTTP_200_OK,
    message="Item Offers Fetched Successfully",
    result_data=result,
  )


@router.get(
    "/{offer_id}",
    response_model=StandardResponse[ItemOfferResponse],
    summary="Get a single item offer by ID",
)
async def get_item_offer_id(
    offer_id: str,
    db=Depends(get_db),
    _: dict = Depends(get_current_user),                
):
    """Fetch one item offer by its ID."""
    result = await ItemOfferController.get_item_by_id(offer_id, db)
    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="Item Offer Fetched Successfully",
        result_data=result,
    )


@router.patch(
   '/{offer_id}',
   response_model=StandardResponse[ItemOfferResponse],
   summary="Update single item offer by ID",
)
async def update_item_offer(
   offer_id: str,
   data: ItemOfferUpdate,
   db=Depends(get_db),
   _: dict = Depends(get_current_user),
):
   result = await ItemOfferController.update_item_offer(offer_id, data, db)
   return StandardResponse(
      status_code=status.HTTP_200_OK,
      message="Item Offer Updated",
      result_data=result
   )


@router.delete(
    "/{offer_id}",
    response_model=StandardResponse[dict],
    summary="Delete a help ticket",
)
async def delete_ticket(
    offer_id: str,
    db=Depends(get_db),
    _: dict = Depends(get_current_user),                
):
    """Hard-delete a help ticket."""
    result = await ItemOfferController.remove_item_offer(offer_id, db)
    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="Item offer Deleted Successfully",
        result_data=result,
    )