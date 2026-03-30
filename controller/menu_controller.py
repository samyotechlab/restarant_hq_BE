import asyncio
import math
import httpx
from datetime import datetime, timezone
from config.settings import settings
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

N8N_WEBHOOK_URL = settings.N8N_CATALOG_SYNC_WEBHOOK


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


def _build_sync_payload(item_doc: dict, sync_type: str = "single") -> dict:
    """Build the n8n webhook payload from a menu item document."""
    return {
        "sync_type": sync_type,
        "item": {
            "id": str(item_doc["_id"]),
            "item_name": item_doc["item_name"],
            "price": item_doc["price"],
            "category": item_doc["category"],
            "offer": item_doc.get("offer"),
            "image": item_doc.get("image"),
            "available": item_doc.get("available", True),
            "type": item_doc.get("type", ""),
        },
    }


async def _do_sync(payload: dict) -> None:
    """Internal actual HTTP call to n8n — runs in background."""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(N8N_WEBHOOK_URL, json=payload)
            print(f"📡 n8n response: {response.status_code} {response.text[:200]}")
    except Exception as e:
        print(f"❌ Catalog sync error: {type(e).__name__}: {str(e)}")


async def _trigger_catalog_sync(payload: dict) -> None:
    """Fire-and-forget — never blocks the main API request."""
    asyncio.create_task(_do_sync(payload))
    print(f"🚀 Catalog sync triggered for: {payload['item'].get('item_name', 'unknown')}")


async def _trigger_catalog_delete(item_id: str) -> None:
    """Fire-and-forget delete — never blocks the main API request."""
    payload = {
        "sync_type": "delete",
        "item": {"item_id": item_id}
    }
    asyncio.create_task(_do_sync(payload)) 
    print(f"🚀 Catalog delete triggered for: {item_id}")


async def _do_bulk_sync(payload: dict) -> None:
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(N8N_WEBHOOK_URL, json=payload)
            print(f"📡 Bulk sync response: {response.status_code} {response.text[:200]}")
    except Exception as e:
        print(f"❌ Bulk catalog sync error: {type(e).__name__}: {str(e)}")


class MenuController:

    @staticmethod
    async def create_item(data: MenuItemCreate, db) -> MenuItemResponse:
        """Create a new menu item and sync to Meta Catalog."""
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

        await _trigger_catalog_sync(_build_sync_payload(item_doc))

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
    async def get_all_items_paginated(
        db, page: int = 1, limit: int = 10
    ) -> PaginatedMenuResponse:
        """Return a paginated list of menu items."""
        skip = (page - 1) * limit
        total_results = await db["menu_items"].count_documents({})
        items = (
            await db["menu_items"]
            .find()
            .skip(skip)
            .limit(limit)
            .sort("created_at", -1)
            .to_list(length=None)
        )
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
        """Fetch all menu items without pagination."""
        items = (
            await db["menu_items"]
            .find()
            .sort("created_at", -1)
            .to_list(length=None)
        )
        return [_to_response(i) for i in items]


    @staticmethod
    async def update_item(
        item_id: str, data: MenuItemUpdate, db
    ) -> MenuItemResponse:
        """Partial update and sync changes to Meta Catalog."""
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

        await _trigger_catalog_sync(_build_sync_payload(updated))

        return _to_response(updated)


    @staticmethod
    async def delete_item(item_id: str, db) -> dict:
        """Hard-delete a menu item and remove from Meta Catalog."""
        _validate_object_id(item_id)

        result = await db["menu_items"].delete_one({"_id": ObjectId(item_id)})
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Menu item not found.",
            )

        # ── Remove from Meta Catalog ──
        await _trigger_catalog_delete(item_id)

        return {"deleted_id": item_id}


    @staticmethod
    async def bulk_create_items(
        data: list[dict], db
    ) -> BulkMenuUploadResponse:
        """
        Insert multiple menu items in one go.
        Validates each item individually — skips failed entries.
        Syncs all successfully inserted items to Meta Catalog.
        """
        results = []
        inserted = 0
        failed = 0
        inserted_docs = []

        for index, raw in enumerate(data):
            try:
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
                inserted_docs.append(item_doc)

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

        if inserted_docs:
            bulk_payload = {
                "sync_type": "full",
                "items": [         
                    {
                        "item_id": str(doc["_id"]),
                        "item_name": doc["item_name"],
                        "price": doc["price"],
                        "category": doc["category"],
                        "offer": doc.get("offer"),
                        "image": doc.get("image"),
                        "available": doc.get("available", True),
                        "type": doc.get("type", ""),
                    }
                    for doc in inserted_docs
                ]
            }
            asyncio.create_task(_do_bulk_sync(bulk_payload))
            print(f"🚀 Bulk catalog sync triggered: {inserted} items")

        return BulkMenuUploadResponse(
            total=len(data),
            inserted=inserted,
            failed=failed,
            results=results,
        )