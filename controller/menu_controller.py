import asyncio
import io
import math
import httpx
import pandas as pd
from datetime import datetime, timezone
from typing import List
from uuid import uuid4
from bson import ObjectId
from fastapi import HTTPException, UploadFile, status

from config.settings import settings
from models.menu_model import (
    BulkMenuUploadResponse,
    BulkMenuUploadResult,
    CSVMenuRow,
    MenuItemCreate,
    MenuItemResponse,
    MenuItemType,
    MenuItemUpdate,
    PaginatedMenuResponse,
)

N8N_WEBHOOK_URL = settings.N8N_CATALOG_SYNC_WEBHOOK


def _to_response(doc: dict) -> MenuItemResponse:
    """Convert a raw MongoDB document → MenuItemResponse."""
    base_price = doc.get("base_price") or doc.get("price") or 0.0
    online_price = doc.get("online_price") or doc.get("price") or 0.0
    
    # Handle old docs that used 'type' instead of 'dietary'
    dietary = doc.get("dietary") or doc.get("type") or MenuItemType.VEG
    return MenuItemResponse(
        id=str(doc["_id"]),
        item_no=doc["item_no"],
        item_name=doc["item_name"],
        category=doc["category"],
        description=doc.get("description"),
        base_price=base_price,
        online_price=online_price,
        dietary=dietary,
        available=doc.get("available", True),
        image=doc.get("image"),
        offer=doc.get("offer"),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


def _build_insert_doc(item: MenuItemCreate, now: datetime) -> dict:
    """Build a full MongoDB document for a brand new item."""
    return {
        "item_no": f"ITEM-{uuid4().hex[:8].upper()}",
        "item_name": item.item_name,
        "category": item.category,
        "description": item.description,
        "base_price": item.base_price,
        "online_price": item.online_price,
        "dietary": item.dietary.value,
        "available": item.available,
        "image": str(item.image) if item.image else None,
        "offer": item.offer,
        "created_at": now,
        "updated_at": now,
    }


def _build_update_fields(item: MenuItemCreate, now: datetime) -> dict:
    """
    Fields that always get updated on re-upload.
    Protects: _id, item_no, created_at, image, offer, available
    (those are managed manually via PATCH API)
    """
    return {
        "item_name": item.item_name,
        "category": item.category,
        "description": item.description,
        "base_price": item.base_price,
        "online_price": item.online_price,
        "dietary": item.dietary.value,
        "updated_at": now,
    }


def _validate_object_id(item_id: str) -> None:
    if not ObjectId.is_valid(item_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"'{item_id}' is not a valid item ID.",
        )


def _build_sync_payload(item_doc: dict, sync_type: str = "single") -> dict:
    return {
        "sync_type": sync_type,
        "item": {
            "id": str(item_doc["_id"]),
            "item_name": item_doc["item_name"],
            "base_price": item_doc["base_price"],
            "online_price": item_doc["online_price"],
            "category": item_doc["category"],
            "offer": item_doc.get("offer"),
            "image": item_doc.get("image"),
            "available": item_doc.get("available", True),
            "dietary": item_doc.get("dietary", ""),
        },
    }


async def _do_sync(payload: dict) -> None:
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(N8N_WEBHOOK_URL, json=payload)
            print(f"📡 n8n: {resp.status_code} {resp.text[:200]}")
    except Exception as e:
        print(f"❌ Sync error: {type(e).__name__}: {e}")


async def _trigger_catalog_sync(payload: dict) -> None:
    asyncio.create_task(_do_sync(payload))
    print(f"🚀 Sync triggered: {payload['item'].get('item_name', '?')}")


async def _trigger_catalog_delete(item_id: str) -> None:
    payload = {"sync_type": "delete", "item": {"item_id": item_id}}
    asyncio.create_task(_do_sync(payload))
    print(f"🚀 Delete triggered: {item_id}")


async def _do_bulk_sync(payload: dict) -> None:
    try:
        async with httpx.AsyncClient(timeout=150.0) as client:
            resp = await client.post(N8N_WEBHOOK_URL, json=payload)
            print(f"📡 Bulk sync: {resp.status_code} {resp.text[:200]}")
    except Exception as e:
        print(f"❌ Bulk sync error: {type(e).__name__}: {e}")


def parse_upload_file(file_bytes: bytes, filename: str) -> List[dict]:
    """Parse CSV or Excel upload → list of raw row dicts."""
    if filename.endswith((".xlsx", ".xls")):
        df = pd.read_excel(io.BytesIO(file_bytes))
    else:
        df = pd.read_csv(io.BytesIO(file_bytes))
    df = df.where(pd.notna(df), None)
    return df.to_dict(orient="records")


class MenuController:

    @staticmethod
    async def create_item(data: MenuItemCreate, db) -> MenuItemResponse:
        """Create a single menu item and sync to WhatsApp Catalog."""
        now = datetime.now(timezone.utc)
        doc = _build_insert_doc(data, now)
        result = await db["menu_items"].insert_one(doc)
        doc["_id"] = result.inserted_id
        await _trigger_catalog_sync(_build_sync_payload(doc))
        return _to_response(doc)


    @staticmethod
    async def get_item(item_id: str, db) -> MenuItemResponse:
        """Fetch a single menu item by MongoDB ID."""
        _validate_object_id(item_id)
        doc = await db["menu_items"].find_one({"_id": ObjectId(item_id)})
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found.")
        return _to_response(doc)


    @staticmethod
    async def get_all_items_paginated(
        db, page: int = 1, limit: int = 10
    ) -> PaginatedMenuResponse:
        """Paginated list of menu items, newest first."""
        skip = (page - 1) * limit
        total = await db["menu_items"].count_documents({})
        items = (
            await db["menu_items"]
            .find()
            .skip(skip)
            .limit(limit)
            # .sort("created_at", -1)
            .to_list(length=None)
        )
        return PaginatedMenuResponse(
            total_results=total,
            page=page,
            limit=limit,
            total_pages=math.ceil(total / limit),
            data=[_to_response(i) for i in items],
        )


    @staticmethod
    async def get_all_items(db) -> List[MenuItemResponse]:
        """All menu items without pagination."""
        items = (
            await db["menu_items"]
            .find()
            .sort("created_at", -1)
            .to_list(length=None)
        )
        return [_to_response(i) for i in items]


    @staticmethod
    async def update_item(item_id: str, data: MenuItemUpdate, db) -> MenuItemResponse:
        """Partial update via PATCH — only provided fields change."""
        _validate_object_id(item_id)

        existing = await db["menu_items"].find_one({"_id": ObjectId(item_id)})
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found.")

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
        """Hard-delete a menu item and remove from WhatsApp Catalog."""
        _validate_object_id(item_id)
        result = await db["menu_items"].delete_one({"_id": ObjectId(item_id)})
        if result.deleted_count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found.")
        await _trigger_catalog_delete(item_id)
        return {"deleted_id": item_id}


    # ── Bulk upload ──────────────────────────────────────────────

    @staticmethod
    async def bulk_upload_from_file(file: UploadFile, db) -> BulkMenuUploadResponse:
        """Accept CSV/Excel file, parse and upsert all rows."""
        if file.filename is None or not file.filename.endswith((".csv", ".xlsx", ".xls")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only .csv, .xlsx, or .xls files are accepted.",
            )
        file_bytes = await file.read()
        raw_rows = parse_upload_file(file_bytes, file.filename)
        return await MenuController.bulk_create_items(raw_rows, db)


    @staticmethod
    async def bulk_create_items(raw_rows: List[dict], db) -> BulkMenuUploadResponse:
        """
        Upsert multiple menu items.
        Match key: item_name + category (unique together).

        On FIRST upload  → inserts full document
        On RE-UPLOAD     → updates only: item_name, category, description,
                           base_price, online_price, type, updated_at
        Never overwrites → _id, item_no, created_at, image, offer, available
        """
        results: List[BulkMenuUploadResult] = []
        inserted = 0
        updated = 0
        failed = 0
        skipped = 0
        synced_docs = []

        for index, raw in enumerate(raw_rows):
            item_name_hint = str(raw.get("ItemName") or raw.get("item_name") or f"Row {index}").strip()

            # Skip blank rows
            values = [v for v in raw.values() if v is not None and str(v).strip() not in ("", "nan")]
            if not values:
                skipped += 1
                continue

            try:
                if "item_name" in raw:
                    item = MenuItemCreate(**raw)
                else:
                    csv_row = CSVMenuRow(**raw)
                    item = csv_row.to_menu_item_create()

                now = datetime.now(timezone.utc)

                existing = await db["menu_items"].find_one({
                    "item_name": item.item_name,
                    "category": item.category,
                })

                if existing:
                    update_fields = _build_update_fields(item, now)
                    await db["menu_items"].update_one(
                        {"_id": existing["_id"]},
                        {"$set": update_fields},
                    )
                    doc = await db["menu_items"].find_one({"_id": existing["_id"]})
                    synced_docs.append(doc)
                    results.append(BulkMenuUploadResult(
                        index=index,
                        success=True,
                        item_name=item.item_name,
                        item=_to_response(doc),
                    ))
                    updated += 1

                else:
                    doc = _build_insert_doc(item, now)
                    result = await db["menu_items"].insert_one(doc)
                    doc["_id"] = result.inserted_id
                    synced_docs.append(doc)
                    results.append(BulkMenuUploadResult(
                        index=index,
                        success=True,
                        item_name=item.item_name,
                        item=_to_response(doc),
                    ))
                    inserted += 1

            except Exception as e:
                results.append(BulkMenuUploadResult(
                    index=index,
                    success=False,
                    item_name=item_name_hint,
                    error=str(e),
                ))
                failed += 1

        if synced_docs:
            bulk_payload = {
                "sync_type": "full",
                "items": [
                    {
                        "item_id": str(d["_id"]),
                        "item_name": d["item_name"],
                        "base_price": d["base_price"],
                        "online_price": d["online_price"],
                        "category": d["category"],
                        "offer": d.get("offer"),
                        "image": d.get("image"),
                        "available": d.get("available", True),
                        "dietary": d.get("dietary", ""),
                    }
                    for d in synced_docs
                ],
            }
            asyncio.create_task(_do_bulk_sync(bulk_payload))
            print(f"🚀 Bulk sync: {inserted} inserted, {updated} updated")

        return BulkMenuUploadResponse(
            total=len(raw_rows),
            inserted=inserted,
            updated=updated,
            failed=failed,
            skipped=skipped,
            results=results,
        )