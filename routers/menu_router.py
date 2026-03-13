from typing import List

from fastapi import APIRouter, Depends, status, Query
from auth.dependencies import get_current_user
from db.database import get_db
from models.menu_model import (
    MenuItemCreate,
    MenuItemResponse,
    MenuItemUpdate,
    PaginatedMenuResponse,
    BulkMenuUploadResponse,
)
from models.base_model import StandardResponse
from controller.menu_controller import MenuController

router = APIRouter(prefix="/menu-item", tags=["Menu"])


@router.post(
    "/",
    response_model=StandardResponse[MenuItemResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new menu item",
)
async def create_menu_item(
    data: MenuItemCreate,
    db=Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """Create a new item on the menu."""
    result = await MenuController.create_item(data, db)
    return StandardResponse(
        status_code=status.HTTP_201_CREATED,
        message="Menu Item Created Successfully",
        result_data=result,
    )


@router.post(
    "/bulk_upload",
    response_model=StandardResponse[BulkMenuUploadResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Bulk upload menu items",
)
async def bulk_upload_menu_items(
    data: list[dict],
    db=Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """
    Upload multiple menu items in one request as a JSON array.
    Failed entries are skipped and reported individually.
    """
    result = await MenuController.bulk_create_items(data, db)
    return StandardResponse(
        status_code=status.HTTP_201_CREATED,
        message="Bulk Menu Upload Completed",
        result_data=result,
    )


@router.get(
    "/",
    response_model=StandardResponse[PaginatedMenuResponse],
    summary="Get all menu items with pagination",
)
async def get_all_menu_items_paginated(
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=10, ge=1, le=100, description="Items per page"),
    db=Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """Return a paginated list of menu items."""
    result = await MenuController.get_all_items_paginated(db, page, limit)
    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="Menu Items Fetched Successfully",
        result_data=result,
    )


@router.get(
    "/fetch_all",
    response_model=StandardResponse[List[MenuItemResponse]],
    summary="Get all menu items",
)
async def get_all_items(db=Depends(get_db)):
    result = await MenuController.get_all_items(db)
    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="Menu Items Fetched Successfully",
        result_data=result
    )


@router.get(
    "/{item_id}",
    response_model=StandardResponse[MenuItemResponse],
    summary="Get a single menu item by ID",
)
async def get_menu_item(
    item_id: str,
    db=Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """Fetch one menu item by its ID."""
    result = await MenuController.get_item(item_id, db)
    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="Menu Item Fetched Successfully",
        result_data=result,
    )


@router.patch(
    "/{item_id}",
    response_model=StandardResponse[MenuItemResponse],
    summary="Partially update a menu item",
)
async def update_menu_item(
    item_id: str,
    data: MenuItemUpdate,
    db=Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """Update one or more fields of a menu item."""
    result = await MenuController.update_item(item_id, data, db)
    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="Menu Item Updated Successfully",
        result_data=result,
    )


@router.delete(
    "/{item_id}",
    response_model=StandardResponse[dict],
    summary="Delete a menu item",
)
async def delete_menu_item(
    item_id: str,
    db=Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """Hard-delete a menu item."""
    result = await MenuController.delete_item(item_id, db)
    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="Menu Item Deleted Successfully",
        result_data=result,
    )