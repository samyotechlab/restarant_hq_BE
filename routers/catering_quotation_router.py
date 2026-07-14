from fastapi import APIRouter, Depends, Query, status
from auth.dependencies import get_current_user
from controller.catering_quotation_controller import CateringQuotationController
from db.database import get_db
from models.base_model import StandardResponse
from models.catering_quotation_model import CateringQuotationResponse, CreateCateringQuotation, PaginatedCateringQuotationResponse, UpdateCateringQuotation

router = APIRouter(prefix="/catering-quotations", tags=['Catering Quotation'])

@router.post(
  '/',
  status_code=status.HTTP_201_CREATED,
  response_model=StandardResponse[CateringQuotationResponse]
)
async def create_catering_quot(data: CreateCateringQuotation, db=Depends(get_db)):
  quot = await CateringQuotationController.create_quotation(data, db)
  return StandardResponse(
    status_code=status.HTTP_201_CREATED,
    message="Catering Quotation Created",
    result_data=quot
  )


@router.get(
  '/',
  response_model=StandardResponse[PaginatedCateringQuotationResponse],
)
async def get_paginated_catering_quot(
  page: int = Query(1, ge=1),
  limit: int = Query(10, ge=1, le=1000),
  db = Depends(get_db),
  _:dict=Depends(get_current_user)
):
  results = await CateringQuotationController.get_quotation_paginated(page, limit, db)
  return StandardResponse(
    status_code=status.HTTP_200_OK,
    message="Paginated Catering Quotations Fetched Successfully",
    result_data=results
  )


@router.get(
  "/{quotation_id}",
  response_model=StandardResponse[CateringQuotationResponse]
)
async def get_one(quotation_id: str, db=Depends(get_db)):
  result = await CateringQuotationController.get_quotation_by_id(quotation_id, db)
  return StandardResponse(
    status_code=status.HTTP_200_OK,
    message="Catering Quotation Fetched",
    result_data=result
  )


@router.patch("/{quotation_id}/status")
async def update_catering_quotation_status(
    quotation_id: str,
    payload: dict,
    db=Depends(get_db)
):
    return await CateringQuotationController.update_quotation_status(
        quotation_id=quotation_id,
        db=db,
        payload=payload,
    )


@router.patch(
  "/{quotation_id}",
  response_model=StandardResponse[CateringQuotationResponse]
)
async def update_quotation(
  quotation_id: str, 
  update_data: UpdateCateringQuotation, 
  db=Depends(get_db),
  _:dict=Depends(get_current_user)
):
  result = await CateringQuotationController.update_quotation(quotation_id, db, update_data)
  return StandardResponse(
    status_code=status.HTTP_200_OK,
    message="Catering Quotation Updated",
    result_data=result
  )


@router.delete(
  "/{quotation_id}",
  response_model=StandardResponse[CateringQuotationResponse]
)
async def remove_quotation(quotation_id: str, db=Depends(get_db), _:dict=Depends(get_current_user)):
  quot = await CateringQuotationController.delete_quotation(quotation_id, db)
  return StandardResponse(
    status_code=status.HTTP_200_OK,
    message="Catering Quotation Deleted",
    result_data=quot
  )