import math
import os
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import HTTPException, status

from models.campaign_model import (
    CampaignCreate,
    CampaignResponse,
    CampaignUpdate,
    PaginatedCampaignResponse,
    Customer,
)


def _validate_object_id(oid: str, label: str = "ID") -> ObjectId:
    if not ObjectId.is_valid(oid):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"'{oid}' is not a valid {label}",
        )
    return ObjectId(oid)


def _to_response(campaign: dict) -> CampaignResponse:
    return CampaignResponse(
        id=str(campaign["_id"]),
        campaign_image=campaign.get("campaign_image"),
        title=campaign.get("title", ""),
        description=campaign.get("description", ""),
        customers=[
            Customer(**c) for c in campaign.get("customers", [])
        ],
        is_sent=campaign.get("is_sent", False),
        created_at=campaign["created_at"],
        updated_at=campaign["updated_at"],
    )


class CampaignController:

    @staticmethod
    async def create_campaign(
        data: CampaignCreate,
        db,
        image_url: str | None,
    ) -> CampaignResponse:
        now = datetime.now(timezone.utc)
        campaign_doc = {
            "campaign_image": image_url,
            "title": data.title,
            "description": data.description,
            "customers": [c.model_dump() for c in data.customers],
            "is_sent": False,
            "created_at": now,
            "updated_at": now,
        }
        result = await db["campaign"].insert_one(campaign_doc)
        campaign_doc["_id"] = result.inserted_id
        return _to_response(campaign_doc)

    
    @staticmethod
    async def get_paginated_campaigns(db, page: int = 1, limit: int = 10):
        skip = (page - 1) * limit
        total = await db["campaign"].count_documents({})
        campaigns = await db["campaign"].find().skip(skip).limit(limit).to_list(length=None)
        return PaginatedCampaignResponse(
            total_results=total,
            page=page,
            total_pages=math.ceil(total / limit),
            limit=limit,
            data=[_to_response(c) for c in campaigns],
        )

    @staticmethod
    async def get_all_campaigns(db):
        campaigns = await db["campaign"].find().sort("created_at", -1).to_list(length=None)
        return [_to_response(c) for c in campaigns]

    @staticmethod
    async def get_one_campaign(campaign_id: str, db):
        _validate_object_id(campaign_id, "Campaign ID")
        campaign = await db["campaign"].find_one({"_id": ObjectId(campaign_id)})
        if not campaign:
            raise HTTPException(404, "Campaign not found")
        return _to_response(campaign)

    @staticmethod
    async def update_campaign(db, campaign_id: str, data: CampaignUpdate):
        _validate_object_id(campaign_id, "Campaign ID")
        existing = await db["campaign"].find_one({"_id": ObjectId(campaign_id)})

        if not existing:
            raise HTTPException(404, "Campaign not found")

        update_fields = data.model_dump(exclude_none=True)

        if "customers" in update_fields:
            update_fields["customers"] = [
                c.model_dump() if hasattr(c, "model_dump") else c
                for c in update_fields["customers"]
            ]

        if update_fields:
            update_fields["updated_at"] = datetime.now(timezone.utc)

            await db["campaign"].update_one(
                {"_id": ObjectId(campaign_id)},
                {"$set": update_fields}
            )

        updated = await db["campaign"].find_one({"_id": ObjectId(campaign_id)})
        return _to_response(updated)
    
    @staticmethod
    async def update_customer_status(db, campaign_id: str, phone_number: str, status: str):
        _validate_object_id(campaign_id, "Campaign ID")

        result = await db["campaign"].update_one(
            {
                "_id": ObjectId(campaign_id),
                "customers.phone_number": phone_number
            },
            {
                "$set": {
                    "customers.$.status": status,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )

        if result.matched_count == 0:
            raise HTTPException(404, "Customer not found in campaign")

        return True

    @staticmethod
    async def remove_campaign(campaign_id: str, db):
        _validate_object_id(campaign_id, "Campaign ID")
        campaign = await db["campaign"].find_one({"_id": ObjectId(campaign_id)})

        if not campaign:
            raise HTTPException(404, "Campaign not found")

        image_path = campaign.get("campaign_image")
        if image_path:
            try:
                local_path = image_path.split("uploads/")[-1]
                full_path = f"uploads/{local_path}"

                if os.path.exists(full_path):
                    os.remove(full_path)

            except Exception as e:
                print("Image deletion failed:", e)

        await db["campaign"].delete_one({"_id": ObjectId(campaign_id)})

        return {"deleted_id": campaign_id}

    @staticmethod
    async def remove_customer(db, campaign_id: str, phone_number: str):
        _validate_object_id(campaign_id, "Campaign ID")
        # Pull the customer with the matching phone number
        result = await db["campaign"].update_one(
            {"_id": ObjectId(campaign_id)},
            {
                "$pull": {"customers": {"phone_number": phone_number}},
                "$set": {"updated_at": datetime.now(timezone.utc)}
            }
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Campaign not found")
        # Return the updated campaign document
        updated = await db["campaign"].find_one({"_id": ObjectId(campaign_id)})
        return _to_response(updated)