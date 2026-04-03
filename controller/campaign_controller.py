import math
from datetime import datetime, timezone
from uuid import uuid4
from bson import ObjectId
from fastapi import HTTPException, status

from models.campaign_model import (
    CampaignCreate,
    CampaignResponse,
    CampaignUpdate,
    CampaignStatus,
    PopulatedMenuItem,
    PaginatedCampaignResponse,
)


def _validate_object_id(oid: str, label: str = "ID") -> None:
    """Raise a 400 early if the provided ID is not a valid MongoDB ObjectId."""
    if not ObjectId.is_valid(oid):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"'{oid}' is not a valid {label}.",
        )


async def _populate_campaign(doc: dict, db) -> CampaignResponse:
    """
    Populate menu_items array — for each stored ObjectId,
    fetch the menu item and return item_name, price, category.
    """
    populated_items = []
    for item_id_str in doc.get("menu_items", []):
        try:
            menu_doc = await db["menu_items"].find_one({"_id": ObjectId(item_id_str)})
            populated_items.append(PopulatedMenuItem(
                menu_item_id=item_id_str,
                item_name=menu_doc.get("item_name") if menu_doc else None,
                price=menu_doc.get("price") if menu_doc else None,
                category=menu_doc.get("category") if menu_doc else None,
            ))
        except Exception:
            continue

    return CampaignResponse(
        id=str(doc["_id"]),
        campaign_id=doc["campaign_id"],
        campaign_type=doc.get("campaign_type"),
        campaign_name=doc.get("campaign_name"),
        description=doc.get("description"),
        menu_items=populated_items,
        offer_price=doc.get("offer_price"),
        discount_percentage=doc.get("discount_percentage"),
        start_date=doc.get("start_date"),
        end_date=doc.get("end_date"),
        status=doc.get("status"),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


class CampaignController:

    @staticmethod
    async def create_campaign(data: CampaignCreate, db) -> CampaignResponse:
        """Create a new marketing campaign."""

        # validate each menu item ObjectId if provided
        for item_id in (data.menu_items or []):
            _validate_object_id(item_id, "menu item ID")
            menu_exists = await db["menu_items"].find_one({"_id": ObjectId(item_id)})
            if not menu_exists:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Menu item '{item_id}' not found.",
                )

        now = datetime.now(timezone.utc)
        campaign_doc = {
            "campaign_id": f"CMP-{uuid4().hex[:8].upper()}",   # e.g. CMP-3F9A1B2C
            "status": data.status.value if data.status else CampaignStatus.SCHEDULED.value,
            "offer_price": data.offer_price or 0,
            "discount_percentage": data.discount_percentage or 0,
            "menu_items": data.menu_items or [],
            "created_at": now,
            "updated_at": now,
            # only store fields that were actually sent
            **{k: v for k, v in data.model_dump(exclude_none=True).items()
               if k not in {"status", "offer_price", "discount_percentage", "menu_items"}},
        }

        result = await db["campaigns"].insert_one(campaign_doc)
        campaign_doc["_id"] = result.inserted_id
        return await _populate_campaign(campaign_doc, db)

    @staticmethod
    async def get_campaign(campaign_id: str, db) -> CampaignResponse:
        """Fetch a single campaign by ID — menu items are populated."""
        _validate_object_id(campaign_id, "campaign ID")

        campaign = await db["campaigns"].find_one({"_id": ObjectId(campaign_id)})
        if not campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaign not found.",
            )
        return await _populate_campaign(campaign, db)

    @staticmethod
    async def get_all_campaigns(db) -> list[CampaignResponse]:
        """Return all campaigns unpaginated."""
        campaigns = await db["campaigns"].find().to_list(length=None)
        return [await _populate_campaign(c, db) for c in campaigns]

    @staticmethod
    async def get_paginated_campaigns(db, page: int = 1, limit: int = 10) -> PaginatedCampaignResponse:
        """Return a paginated list of campaigns."""
        skip = (page - 1) * limit

        total_results = await db["campaigns"].count_documents({})
        campaigns = await db["campaigns"].find().skip(skip).limit(limit).sort('created_at', -1).to_list(length=None)
        total_pages = math.ceil(total_results / limit)

        return PaginatedCampaignResponse(
            total_results=total_results,
            page=page,
            limit=limit,
            total_pages=total_pages,
            data=[await _populate_campaign(c, db) for c in campaigns],
        )

    @staticmethod
    async def update_campaign(campaign_id: str, data: CampaignUpdate, db) -> CampaignResponse:
        """Partial update — only the fields provided in the request body are changed."""
        _validate_object_id(campaign_id, "campaign ID")

        existing = await db["campaigns"].find_one({"_id": ObjectId(campaign_id)})
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaign not found.",
            )

        update_fields = data.model_dump(exclude_none=True)
        if not update_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields provided to update.",
            )

        # validate menu item IDs if being updated
        if "menu_items" in update_fields:
            for item_id in update_fields["menu_items"]:
                _validate_object_id(item_id, "menu item ID")
                menu_exists = await db["menu_items"].find_one({"_id": ObjectId(item_id)})
                if not menu_exists:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Menu item '{item_id}' not found.",
                    )

        # convert enums to values
        if "status" in update_fields and hasattr(update_fields["status"], "value"):
            update_fields["status"] = update_fields["status"].value
        if "campaign_type" in update_fields and hasattr(update_fields["campaign_type"], "value"):
            update_fields["campaign_type"] = update_fields["campaign_type"].value

        update_fields["updated_at"] = datetime.now(timezone.utc)
        await db["campaigns"].update_one(
            {"_id": ObjectId(campaign_id)},
            {"$set": update_fields},
        )

        updated = await db["campaigns"].find_one({"_id": ObjectId(campaign_id)})
        return await _populate_campaign(updated, db)

    @staticmethod
    async def delete_campaign(campaign_id: str, db) -> dict:
        """Hard-delete a campaign."""
        _validate_object_id(campaign_id, "campaign ID")

        result = await db["campaigns"].delete_one({"_id": ObjectId(campaign_id)})
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaign not found.",
            )
        return {"deleted_id": campaign_id}