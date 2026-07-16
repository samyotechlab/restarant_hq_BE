from pathlib import Path
import shutil
from typing import List
from uuid import uuid4
from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from auth.dependencies import get_current_user
from controller.catering_quotation_controller import CateringQuotationController
from db.database import get_db
from models.base_model import StandardResponse
from models.catering_quotation_model import CateringQuotationResponse, CreateCateringQuotation, PaginatedCateringQuotationResponse, UpdateCateringQuotation

router = APIRouter(prefix="/catering-quotations", tags=['Catering Quotation'])

UPLOAD_DIR = Path("uploads/quotations")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

def save_menu_file(file: UploadFile) -> dict:
  ext = Path(file.filename).suffix if file.filename else ""
  unique_name = f"{uuid4().hex}{ext}"
  file_path = UPLOAD_DIR / unique_name

  with open(file_path, "wb") as buffer:
    shutil.copyfileobj(file.file, buffer)

  return {
    "menu_file_url": f"/uploads/quotations/{unique_name}",  
    "menu_file_name": file.filename,
  }


def delete_physical_file(file_url: str | None):
  if not file_url:
    return

  prefix = "/uploads/"
  if not file_url.startswith(prefix):
    return

  relative_path = file_url[len(prefix):]
  file_path = Path("uploads") / relative_path

  if file_path.exists() and file_path.is_file():
    file_path.unlink()


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


@router.post(
  "/{quotation_id}/menu-file",
  response_model=StandardResponse[CateringQuotationResponse],
)
async def upload_attachment(
  quotation_id: str,
  menu_file: UploadFile = File(...),
  db=Depends(get_db),
  _: dict = Depends(get_current_user),
):
  existing = await CateringQuotationController.get_quotation_by_id(quotation_id, db)
  file_data = save_menu_file(menu_file)
  update_data = UpdateCateringQuotation(
      menu_file_url=file_data["menu_file_url"],
      menu_file_name=file_data["menu_file_name"],
  )
  updated = await CateringQuotationController.update_quotation(quotation_id, db, update_data)
  if existing.menu_file_url and existing.menu_file_url != file_data["menu_file_url"]:
      delete_physical_file(existing.menu_file_url)

  return StandardResponse(
      status_code=status.HTTP_200_OK,
      message="Menu File Uploaded Successfully",
      result_data=updated,
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
  "/fetch_all",
  response_model=StandardResponse[List[CateringQuotationResponse]]
)
async def get_all_quotations(db=Depends(get_db), _:dict=Depends(get_current_user)):
  quot = await CateringQuotationController.get_all_quotations(db)
  return StandardResponse(
    status_code=status.HTTP_200_OK,
    message="All Catering Quotation Fetched",
    result_data=quot
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