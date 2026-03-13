import math
from datetime import datetime, timezone
from uuid import uuid4
from bson import ObjectId
from fastapi import HTTPException, status

from models.enquiry_model import (
    EnquiryCreate,
    EnquiryResponse,
    EnquiryUpdate,
    EnquiryStatus,
    PaginatedEnquiryResponse,
)


def _to_response(doc: dict) -> EnquiryResponse:
    """Convert a raw MongoDB document into an EnquiryResponse."""
    return EnquiryResponse(
        id=str(doc["_id"]),
        enquiry_id=doc["enquiry_id"],
        name=doc.get("name"),
        country_code=doc.get("country_code"),
        phone_number=doc.get("phone_number"),
        service=doc.get("service"),
        source=doc.get("source"),
        status=doc["status"],
        assigned_to=doc.get("assigned_to"),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


def _validate_object_id(enquiry_id: str) -> None:
    """Raise a 400 early if the provided ID is not a valid MongoDB ObjectId."""
    if not ObjectId.is_valid(enquiry_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"'{enquiry_id}' is not a valid enquiry ID.",
        )


class EnquiryController:

    @staticmethod
    async def create_enquiry(data: EnquiryCreate, db) -> EnquiryResponse:
        """Create a new enquiry."""
        now = datetime.now(timezone.utc)
        enquiry_doc = {
            "enquiry_id": f"ENQ-{uuid4().hex[:8].upper()}",
            "status": data.status.value if data.status else EnquiryStatus.NEW.value,
            "created_at": now,
            "updated_at": now,
            **{k: v for k, v in data.model_dump(exclude_none=True).items() if k != "status"},
        }

        result = await db["enquiries"].insert_one(enquiry_doc)
        enquiry_doc["_id"] = result.inserted_id
        return _to_response(enquiry_doc)

    @staticmethod
    async def get_enquiry(enquiry_id: str, db) -> EnquiryResponse:
        """Fetch a single enquiry by ID."""
        _validate_object_id(enquiry_id)

        enquiry = await db["enquiries"].find_one({"_id": ObjectId(enquiry_id)})
        if not enquiry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Enquiry not found.",
            )
        return _to_response(enquiry)

    @staticmethod
    async def get_all_enquiries(db, page: int = 1, limit: int = 10) -> PaginatedEnquiryResponse:
        """Return a paginated list of enquiries."""
        skip = (page - 1) * limit

        total_results = await db["enquiries"].count_documents({})
        enquiries = await db["enquiries"].find().skip(skip).limit(limit).to_list(length=None)
        total_pages = math.ceil(total_results / limit)

        return PaginatedEnquiryResponse(
            total_results=total_results,
            page=page,
            limit=limit,
            total_pages=total_pages,
            data=[_to_response(e) for e in enquiries],
        )

    @staticmethod
    async def update_enquiry(enquiry_id: str, data: EnquiryUpdate, db) -> EnquiryResponse:
        """Partial update — only the fields provided in the request body are changed."""
        _validate_object_id(enquiry_id)

        existing = await db["enquiries"].find_one({"_id": ObjectId(enquiry_id)})
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Enquiry not found.",
            )

        update_fields = data.model_dump(exclude_none=True)
        if not update_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields provided to update.",
            )

        update_fields["updated_at"] = datetime.now(timezone.utc)
        await db["enquiries"].update_one(
            {"_id": ObjectId(enquiry_id)},
            {"$set": update_fields},
        )

        updated = await db["enquiries"].find_one({"_id": ObjectId(enquiry_id)})
        return _to_response(updated)

    @staticmethod
    async def delete_enquiry(enquiry_id: str, db) -> dict:
        """Hard-delete an enquiry."""
        _validate_object_id(enquiry_id)

        result = await db["enquiries"].delete_one({"_id": ObjectId(enquiry_id)})
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Enquiry not found.",
            )
        return {"deleted_id": enquiry_id}