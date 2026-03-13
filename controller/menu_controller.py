import math
from datetime import datetime, timezone
from typing import List
from uuid import uuid4
from bson import ObjectId
from fastapi import HTTPException, status

from models.menu_model import (
    MenuItemCreate,
    MenuItemResponse,
    MenuItemUpdate,
    MenuItemType,
    PaginatedMenuResponse,
    BulkMenuUploadResult,
    BulkMenuUploadResponse,
)


def _to_response(doc: dict) -> MenuItemResponse:
    """Convert a raw MongoDB document into a MenuItemResponse."""
    return MenuItemResponse(
        id=str(doc["_id"]),
        item_no=doc["item_no"],
        image=doc["image"],
        item_name=doc["item_name"],
        category=doc["category"],
        price=doc["price"],
        type=doc["type"],
        offer=doc["offer"],
        available=doc["available"],
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


def _validate_object_id(item_id: str) -> None:
    """Raise a 400 early if the provided ID is not a valid MongoDB ObjectId."""
    if not ObjectId.is_valid(item_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"'{item_id}' is not a valid item ID.",
        )


class MenuController:

    @staticmethod
    async def create_item(data: MenuItemCreate, db) -> MenuItemResponse:
        """Create a new menu item."""
        now = datetime.now(timezone.utc)
        item_doc = {
            "item_no": f"ITEM-{uuid4().hex[:8].upper()}",
            "image": str(data.image) if data.image else None,
            "item_name": data.item_name,
            "category": data.category,
            "price": data.price,
            "type": data.type.value,
            "offer": data.offer,
            "available": data.available,
            "created_at": now,
            "updated_at": now,
        }

        result = await db["menu_items"].insert_one(item_doc)
        item_doc["_id"] = result.inserted_id
        return _to_response(item_doc)

    @staticmethod
    async def get_item(item_id: str, db) -> MenuItemResponse:
        """Fetch a single menu item by ID."""
        _validate_object_id(item_id)

        item = await db["menu_items"].find_one({"_id": ObjectId(item_id)})
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Menu item not found.",
            )
        return _to_response(item)

    @staticmethod
    async def get_all_items_paginated(db, page: int = 1, limit: int = 10) -> PaginatedMenuResponse:
        """Return a paginated list of menu items."""
        skip = (page - 1) * limit
        total_results = await db["menu_items"].count_documents({})
        items = await db["menu_items"].find().skip(skip).limit(limit).to_list(length=None)
        total_pages = math.ceil(total_results / limit)

        return PaginatedMenuResponse(
            total_results=total_results,
            page=page,
            limit=limit,
            total_pages=total_pages,
            data=[_to_response(i) for i in items],
        )

    @staticmethod
    async def get_all_items(db) -> List[MenuItemResponse]:
        items = await db['menu_items'].find().sort('created_at', -1).to_list(length=None)
        return [_to_response(i) for i in items]


    @staticmethod
    async def update_item(item_id: str, data: MenuItemUpdate, db) -> MenuItemResponse:
        """Partial update — only fields provided are changed."""
        _validate_object_id(item_id)

        existing = await db["menu_items"].find_one({"_id": ObjectId(item_id)})
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Menu item not found.",
            )

        update_fields = data.model_dump(exclude_none=True)
        if not update_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields provided to update.",
            )

        if "image" in update_fields:
            update_fields["image"] = str(update_fields["image"])

        update_fields["updated_at"] = datetime.now(timezone.utc)
        await db["menu_items"].update_one(
            {"_id": ObjectId(item_id)},
            {"$set": update_fields},
        )

        updated = await db["menu_items"].find_one({"_id": ObjectId(item_id)})
        return _to_response(updated)

    @staticmethod
    async def delete_item(item_id: str, db) -> dict:
        """Hard-delete a menu item."""
        _validate_object_id(item_id)

        result = await db["menu_items"].delete_one({"_id": ObjectId(item_id)})
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Menu item not found.",
            )
        return {"deleted_id": item_id}

    @staticmethod
    async def bulk_create_items(data: list[dict], db) -> BulkMenuUploadResponse:
        """
        Insert multiple menu items in one go.
        Validates each item individually — skips failed entries.
        """
        results = []
        inserted = 0
        failed = 0

        for index, raw in enumerate(data):
            try:
                # validate each row individually so bad rows don't kill the whole batch
                item = MenuItemCreate(**raw)

                now = datetime.now(timezone.utc)
                item_doc = {
                    "item_no": f"ITEM-{uuid4().hex[:8].upper()}",
                    "image": str(item.image) if item.image else None,
                    "item_name": item.item_name,
                    "category": item.category,
                    "price": item.price,
                    "type": item.type.value,
                    "offer": item.offer,
                    "available": item.available,
                    "created_at": now,
                    "updated_at": now,
                }

                result = await db["menu_items"].insert_one(item_doc)
                item_doc["_id"] = result.inserted_id

                results.append(BulkMenuUploadResult(
                    index=index,
                    success=True,
                    item=_to_response(item_doc),
                ))
                inserted += 1

            except Exception as e:
                results.append(BulkMenuUploadResult(
                    index=index,
                    success=False,
                    error=str(e),
                ))
                failed += 1

        return BulkMenuUploadResponse(
            total=len(data),
            inserted=inserted,
            failed=failed,
            results=results,
        )