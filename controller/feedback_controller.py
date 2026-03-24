import math
from datetime import datetime, timezone
from uuid import uuid4
from bson import ObjectId
from fastapi import HTTPException, status

from models.feedback_model import (
    FeedbackCreate,
    FeedbackResponse,
    FeedbackUpdate,
    PopulatedFeedbackCustomer,
    PopulatedFeedbackOrder,
    PaginatedFeedbackResponse,
)


def _validate_object_id(oid: str, label: str = "ID") -> None:
    """Raise a 400 early if the provided ID is not a valid MongoDB ObjectId."""
    if not ObjectId.is_valid(oid):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"'{oid}' is not a valid {label}.",
        )


async def _populate_feedback(doc: dict, db) -> FeedbackResponse:
    """
    Populate customer and order fields and include granular ratings.
    """
    
    populated_customer = None
    if doc.get("customer"):
        try:
            customer_doc = await db["customers"].find_one({"_id": ObjectId(doc["customer"])})
            if customer_doc:
                populated_customer = PopulatedFeedbackCustomer(
                    customer_id=customer_doc.get("customer_id"),
                    name=customer_doc.get("name"),
                    phone_number=customer_doc.get("phone_number"),
                )
        except Exception:
            pass

    
    populated_order = None
    if doc.get("order"):
        try:
            order_doc = await db["orders"].find_one({"_id": ObjectId(doc["order"])})
            if order_doc:
                populated_order = PopulatedFeedbackOrder(
                    order_id=order_doc.get("order_id"),
                    grand_total=order_doc.get("grand_total"),
                    status=order_doc.get("status"),
                )
        except Exception:
            pass

    return FeedbackResponse(
        id=str(doc["_id"]),
        feedback_id=doc["feedback_id"],
        customer=populated_customer,
        order=populated_order,
        phone_number=doc.get("phone_number"),
        overall_rating=doc.get("overall_rating"),
        food_quality_rating=doc.get("food_quality_rating"),
        delivery_rating=doc.get("delivery_rating"),
        comment=doc.get("comment"),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )

class FeedbackController:

    @staticmethod
    async def create_feedback(data: FeedbackCreate, db) -> FeedbackResponse:
        """Create a new feedback entry."""

       
        if data.customer:
            _validate_object_id(data.customer, "customer ID")
            customer_exists = await db["customers"].find_one({"_id": ObjectId(data.customer)})
            if not customer_exists:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Customer not found.",
                )

        
        if data.order:
            _validate_object_id(data.order, "order ID")
            order_exists = await db["orders"].find_one({"_id": ObjectId(data.order)})
            if not order_exists:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Order not found.",
                )

        now = datetime.now(timezone.utc)
        feedback_doc = {
            "feedback_id": f"FDB-{uuid4().hex[:8].upper()}",   # e.g. FDB-3F9A1B2C
            "created_at": now,
            "updated_at": now,
            **{k: v for k, v in data.model_dump(exclude_none=True).items()
               if k != "status"},
        }

        result = await db["feedback"].insert_one(feedback_doc)
        feedback_doc["_id"] = result.inserted_id
        return await _populate_feedback(feedback_doc, db)

    @staticmethod
    async def fetch_all_feedback(db) -> list[FeedbackResponse]:
        """Return all feedback unpaginated."""
        feedbacks = await db["feedback"].find().sort("created_at", -1).to_list(length=None)
        return [await _populate_feedback(f, db) for f in feedbacks]

    @staticmethod
    async def get_paginated_feedback(db, page: int = 1, limit: int = 10) -> PaginatedFeedbackResponse:
        """Return a paginated list of feedback."""
        skip = (page - 1) * limit

        total_results = await db["feedback"].count_documents({})
        feedbacks = await db["feedback"].find().skip(skip).limit(limit).sort("created_at", -1).to_list(length=None)
        total_pages = math.ceil(total_results / limit)

        return PaginatedFeedbackResponse(
            total_results=total_results,
            page=page,
            limit=limit,
            total_pages=total_pages,
            data=[await _populate_feedback(f, db) for f in feedbacks],
        )

    @staticmethod
    async def get_feedback(feedback_id: str, db) -> FeedbackResponse:
        """Fetch a single feedback by ID."""
        _validate_object_id(feedback_id, "feedback ID")

        feedback = await db["feedback"].find_one({"_id": ObjectId(feedback_id)})
        if not feedback:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Feedback not found.",
            )
        return await _populate_feedback(feedback, db)

    @staticmethod
    async def update_feedback(feedback_id: str, data: FeedbackUpdate, db) -> FeedbackResponse:
        """Partial update supports granular ratings."""
        _validate_object_id(feedback_id, "feedback ID")

        existing = await db["feedback"].find_one({"_id": ObjectId(feedback_id)})
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Feedback not found.",
            )

        update_fields = data.model_dump(exclude_none=True)
        if not update_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields provided to update.",
            )

        if "customer" in update_fields:
            _validate_object_id(update_fields["customer"], "customer ID")
           
            
        if "order" in update_fields:
            _validate_object_id(update_fields["order"], "order ID")
           

        if "status" in update_fields and hasattr(update_fields["status"], "value"):
            update_fields["status"] = update_fields["status"].value

        update_fields["updated_at"] = datetime.now(timezone.utc)
        await db["feedback"].update_one(
            {"_id": ObjectId(feedback_id)},
            {"$set": update_fields},
        )

        updated = await db["feedback"].find_one({"_id": ObjectId(feedback_id)})
        return await _populate_feedback(updated, db)

    @staticmethod
    async def delete_feedback(feedback_id: str, db) -> dict:
        """Hard-delete a feedback entry."""
        _validate_object_id(feedback_id, "feedback ID")

        result = await db["feedback"].delete_one({"_id": ObjectId(feedback_id)})
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Feedback not found.",
            )
        return {"deleted_id": feedback_id}