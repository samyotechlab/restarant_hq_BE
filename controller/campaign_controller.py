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


def _to_response(doc: dict) -> CampaignResponse:
    customers = doc.get("customers", [])
    total     = len(customers)
    sent      = sum(1 for c in customers if (c.get("status") or "").lower() == "sent")
    read      = sum(1 for c in customers if (c.get("status") or "").lower() == "read")
    failed    = sum(1 for c in customers if (c.get("status") or "").lower() == "failed")
    error     = sum(1 for c in customers if (c.get("status") or "").lower() == "error")

    return CampaignResponse(
        id=str(doc["_id"]),
        campaign_image=doc.get("campaign_image"),
        title=doc.get("title", ""),
        description=doc.get("description", ""),
        customers=[Customer(**c) for c in customers],
        is_sent=doc.get("is_sent", False),
        created_at=doc.get("created_at"),
        updated_at=doc.get("updated_at"),
        total_customers=total,
        sent_count=sent,
        read_count=read,
        failed_count=failed,
        error_count=error,
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
        campaigns = await db["campaign"].find().skip(skip).sort("created_at", -1).limit(limit).to_list(length=None)
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
    async def update_customer_status(db, campaign_id: str, phone_number: str, new_status: str, fail_reason: str | None = None):
        _validate_object_id(campaign_id, "Campaign ID")
        
        set_fields = {
            "customers.$.status": new_status,
            "updated_at": datetime.now(timezone.utc),
        }
        s = new_status.lower()
        if s == "sent":
            set_fields["customers.$.sent_at"] = datetime.now(timezone.utc)
        elif s == "read":
            set_fields["customers.$.read_at"] = datetime.now(timezone.utc)
        elif s in ("failed", "error") and fail_reason:
            set_fields["customers.$.fail_reason"] = fail_reason
        
        result = await db["campaign"].update_one(
            {
                "_id": ObjectId(campaign_id),
                "customers.phone_number": phone_number
            },
            {"$set": set_fields}
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
    
    @staticmethod
    async def get_all_used_phones(db) -> list[str]:
        campaigns = await db["campaign"].find(
            {}, {"customers.phone_number": 1}
        ).to_list(length=None)

        phones = set()
        for c in campaigns:
            for cust in c.get("customers", []):
                if p := cust.get("phone_number"):
                    phones.add(str(p))
        return list(phones)