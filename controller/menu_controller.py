import asyncio
from collections import defaultdict
import csv
import io
import math
import os
import httpx
import pandas as pd
from datetime import datetime, timezone
from typing import AsyncGenerator, List
from uuid import uuid4
from bson import ObjectId
from fastapi import HTTPException, UploadFile, status
from openpyxl import load_workbook
from config.settings import settings
import re
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

def _make_search_name(name: str) -> str:
    if not name:
        return ""
    name = name.lower()
    name = re.sub(r"[^\w\s]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name

def _to_response(doc: dict) -> MenuItemResponse:
    base_price = doc.get("base_price") or doc.get("price") or 0.0
    online_price = doc.get("online_price") or doc.get("price") or 0.0
    dietary = doc.get("dietary") or doc.get("type") or MenuItemType.VEG
    return MenuItemResponse(
        id=str(doc["_id"]),
        item_no=doc["item_no"],
        item_name=doc["item_name"],
        search_name=doc.get("search_name"),
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
    return {
        "item_no": f"ITEM-{uuid4().hex[:8].upper()}",
        "item_name": item.item_name,
        "search_name":  _make_search_name(item.item_name),
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
    return {
        "item_name": item.item_name,
        "search_name": _make_search_name(item.item_name),
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
            "description": item_doc.get("description", ""),
            "base_price": item_doc.get("base_price", 0.0),
            "online_price": item_doc.get("online_price", 0.0),
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


async def _stream_csv(file_path: str) -> AsyncGenerator[dict, None]:
    """Fixed: file handle stays open while iterating rows."""
    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:          # ← inside `with`, not outside
            yield row


async def _stream_excel(file_path: str) -> AsyncGenerator[dict, None]:
    """Fixed: yields every data row, not only the final one."""
    wb = load_workbook(file_path, read_only=True)
    ws = wb.active
    if ws is None:
        wb.close()
        return
    headers = None
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i == 0:
            headers = [str(h).strip() if h is not None else f"col_{i}" for i, h in enumerate(row)]
            continue
        if headers:
            yield dict(zip(headers, row))
    wb.close()


class MenuController:

    @staticmethod
    async def create_item(data: MenuItemCreate, db) -> MenuItemResponse:
        now = datetime.now(timezone.utc)
        doc = _build_insert_doc(data, now)
        result = await db["menu_items"].insert_one(doc)
        doc["_id"] = result.inserted_id
        await _trigger_catalog_sync(_build_sync_payload(doc))
        return _to_response(doc)

    @staticmethod
    async def get_item(item_id: str, db) -> MenuItemResponse:
        _validate_object_id(item_id)
        doc = await db["menu_items"].find_one({"_id": ObjectId(item_id)})
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found.")
        return _to_response(doc)
    
    @staticmethod
    async def get_limit_fields(db):
        cursor = db['menu_items'].find(
            {"available": True},
            {"_id":1, "item_name":1,"search_name":1,"category": 1,"online_price":1, "dietary":1})
        docs = await cursor.to_list(length=None)
        categorized = defaultdict(list)
        for item in docs:
            category = item.get("category", "Others")
            categorized[category].append({
                    "id": str(item['_id']),
                    "item_name": item.get("item_name"),
                    "search_name": item.get("search_name"),
                    "description": item.get("description"),
                    "price": item.get('online_price'),
                    "dietary": item.get("dietary")
                })
            
        return dict(categorized)

    @staticmethod
    async def get_all_items_paginated(db, page: int = 1, limit: int = 10) -> PaginatedMenuResponse:
        skip = (page - 1) * limit
        total = await db["menu_items"].count_documents({})
        items = await db["menu_items"].find().skip(skip).limit(limit).to_list(length=None)
        return PaginatedMenuResponse(
            total_results=total,
            page=page,
            limit=limit,
            total_pages=math.ceil(total / limit),
            data=[_to_response(i) for i in items],
        )

    @staticmethod
    async def get_all_items(db) -> List[MenuItemResponse]:
        items = await db["menu_items"].find().sort("created_at", -1).to_list(length=None)
        return [_to_response(i) for i in items]

    @staticmethod
    async def update_item(item_id: str, data: MenuItemUpdate, db) -> MenuItemResponse:
        _validate_object_id(item_id)
        existing = await db["menu_items"].find_one({"_id": ObjectId(item_id)})
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found.")
        update_fields = data.model_dump(exclude_none=True)
        if not update_fields:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields provided to update.")
        if "item_name" in update_fields:
            update_fields["search_name"] = _make_search_name(update_fields["item_name"])
        if "image" in update_fields:
            update_fields["image"] = str(update_fields["image"])
        update_fields["updated_at"] = datetime.now(timezone.utc)
        await db["menu_items"].update_one({"_id": ObjectId(item_id)}, {"$set": update_fields})
        updated = await db["menu_items"].find_one({"_id": ObjectId(item_id)})
        await _trigger_catalog_sync(_build_sync_payload(updated))
        return _to_response(updated)

    @staticmethod
    async def delete_item(item_id: str, db) -> dict:
        _validate_object_id(item_id)
        result = await db["menu_items"].delete_one({"_id": ObjectId(item_id)})
        if result.deleted_count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found.")
        await _trigger_catalog_delete(item_id)
        return {"deleted_id": item_id}

    @staticmethod
    async def bulk_upload_from_file_path(file_path: str, db) -> dict:
        inserted = 0
        updated = 0
        failed = 0
        synced_docs = []

        try:
            if file_path.endswith(".csv"):
                async for row in _stream_csv(file_path):
                    res = await MenuController._process_row(row, db)
                    inserted += res["inserted"]
                    updated += res["updated"]
                    failed += res["failed"]
                    if res.get("doc"):
                        synced_docs.append(res["doc"])

            elif file_path.endswith((".xlsx", ".xls")):
                async for row in _stream_excel(file_path):
                    res = await MenuController._process_row(row, db)
                    inserted += res["inserted"]
                    updated += res["updated"]
                    failed += res["failed"]
                    if res.get("doc"):
                        synced_docs.append(res["doc"])

        finally:
            if os.path.exists(file_path):
                os.remove(file_path)

        if synced_docs:
            bulk_payload = {
                "sync_type": "full",
                "items": [
                    {
                        "item_id": str(d["_id"]),
                        "item_name": d["item_name"],
                        "description": d.get("description", ""),
                        "base_price": d.get("base_price", 0.0),
                        "online_price": d.get("online_price", 0.0),
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

        print(f"✅ Done: {inserted} inserted, {updated} updated, {failed} failed")
        return {"inserted": inserted, "updated": updated, "failed": failed}

    @staticmethod
    async def _process_row(raw: dict, db) -> dict:
        """Process a single raw CSV/Excel row → upsert in DB. Returns counts + doc."""
        values = [v for v in raw.values() if v is not None and str(v).strip() not in ("", "nan")]
        if not values:
            return {"inserted": 0, "updated": 0, "failed": 0, "doc": None}

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
                await db["menu_items"].update_one({"_id": existing["_id"]}, {"$set": update_fields})
                doc = await db["menu_items"].find_one({"_id": existing["_id"]})
                return {"inserted": 0, "updated": 1, "failed": 0, "doc": doc}
            else:
                doc = _build_insert_doc(item, now)
                result = await db["menu_items"].insert_one(doc)
                doc["_id"] = result.inserted_id
                return {"inserted": 1, "updated": 0, "failed": 0, "doc": doc}

        except Exception as e:
            print(f"❌ Row failed: {e} | row={raw}")
            return {"inserted": 0, "updated": 0, "failed": 1, "doc": None}

    @staticmethod
    async def bulk_create_items(raw_rows: List[dict], db) -> BulkMenuUploadResponse:
        results: List[BulkMenuUploadResult] = []
        inserted = 0
        updated = 0
        failed = 0
        skipped = 0
        synced_docs = []

        for index, raw in enumerate(raw_rows):
            item_name_hint = str(raw.get("ItemName") or raw.get("item_name") or f"Row {index}").strip()

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
                    await db["menu_items"].update_one({"_id": existing["_id"]}, {"$set": update_fields})
                    doc = await db["menu_items"].find_one({"_id": existing["_id"]})
                    synced_docs.append(doc)
                    results.append(BulkMenuUploadResult(
                        index=index, success=True, item_name=item.item_name, item=_to_response(doc)
                    ))
                    updated += 1
                else:
                    doc = _build_insert_doc(item, now)
                    result = await db["menu_items"].insert_one(doc)
                    doc["_id"] = result.inserted_id
                    synced_docs.append(doc)
                    results.append(BulkMenuUploadResult(
                        index=index, success=True, item_name=item.item_name, item=_to_response(doc)
                    ))
                    inserted += 1

            except Exception as e:
                results.append(BulkMenuUploadResult(
                    index=index, success=False, item_name=item_name_hint, error=str(e)
                ))
                failed += 1

        if synced_docs:
            bulk_payload = {
                "sync_type": "full",
                "items": [
                    {
                        "item_id": str(d["_id"]),
                        "item_name": d["item_name"],
                        "description": d.get("description", ""),
                        "base_price": d.get("base_price", 0.0),
                        "online_price": d.get("online_price", 0.0),
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