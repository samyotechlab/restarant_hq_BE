import math
from datetime import datetime, timezone
from typing import List
from uuid import uuid4
from bson import ObjectId
from fastapi import HTTPException, status

from models.services_model import (
    ServiceCreate,
    ServiceResponse,
    ServiceUpdate,
    PaginatedServiceResponse,
)


def _to_response(doc: dict) -> ServiceResponse:
    """Convert a raw MongoDB document into a ServiceResponse."""
    return ServiceResponse(
        id=str(doc["_id"]),
        service_id=doc["service_id"],
        service_name=doc["service_name"],
        description=doc["description"],
        pricing=doc["pricing"],
        coverage_area=doc["coverage_area"],
        is_active=doc["is_active"],
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


def _validate_object_id(service_id: str) -> None:
    """Raise a 400 early if the provided ID is not a valid MongoDB ObjectId."""
    if not ObjectId.is_valid(service_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"'{service_id}' is not a valid service ID.",
        )


class ServiceController:

    @staticmethod
    async def create_service(data: ServiceCreate, db) -> ServiceResponse:
        """Create a new service."""
        now = datetime.now(timezone.utc)
        service_doc = {
            "service_id": f"SRV-{uuid4().hex[:8].upper()}",
            "service_name": data.service_name,
            "description": data.description,
            "pricing": data.pricing,
            "coverage_area": data.coverage_area,
            "is_active": data.is_active,
            "created_at": now,
            "updated_at": now,
        }

        result = await db["services"].insert_one(service_doc)
        service_doc["_id"] = result.inserted_id
        return _to_response(service_doc)

    @staticmethod
    async def get_all_services_paginated(db, page: int = 1, limit: int = 8) -> PaginatedServiceResponse:
        """Return a paginated list of services."""
        skip = (page - 1) * limit

        total_results = await db["services"].count_documents({})
        services = await db["services"].find().skip(skip).limit(limit).to_list(length=None)
        total_pages = math.ceil(total_results / limit)

        return PaginatedServiceResponse(
            total_results=total_results,
            page=page,
            limit=limit,
            total_pages=total_pages,
            data=[_to_response(s) for s in services],
        )
    
    @staticmethod
    async def get_all_services(db) -> List[ServiceResponse]:
        services = await db['services'].find().sort('created_at', -1).to_list(length=None)
        return [_to_response(s) for s in services]

    @staticmethod
    async def update_service(service_id: str, data: ServiceUpdate, db) -> ServiceResponse:
        """Partial update — only the fields provided in the request body are changed."""
        _validate_object_id(service_id)

        existing = await db["services"].find_one({"_id": ObjectId(service_id)})
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service not found.",
            )

        update_fields = data.model_dump(exclude_none=True)
        if not update_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields provided to update.",
            )

        update_fields["updated_at"] = datetime.now(timezone.utc)
        await db["services"].update_one(
            {"_id": ObjectId(service_id)},
            {"$set": update_fields},
        )

        updated = await db["services"].find_one({"_id": ObjectId(service_id)})
        return _to_response(updated)

    @staticmethod
    async def delete_service(service_id: str, db) -> dict:
        """Hard-delete a service."""
        _validate_object_id(service_id)

        result = await db["services"].delete_one({"_id": ObjectId(service_id)})
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service not found.",
            )
        return {"deleted_id": service_id}