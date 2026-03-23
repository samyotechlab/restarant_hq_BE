import math
from datetime import datetime, timezone
from uuid import uuid4
from bson import ObjectId
from fastapi import HTTPException, status

from models.help_ticket_model import (
    HelpTicketCreate,
    HelpTicketResponse,
    HelpTicketUpdate,
    TicketStatus,
    TicketSource,
    TicketPriority,
    PopulatedTicketCustomer,
    PaginatedHelpTicketResponse,
)


def _validate_object_id(oid: str, label: str = "ID") -> None:
    """Raise a 400 early if the provided ID is not a valid MongoDB ObjectId."""
    if not ObjectId.is_valid(oid):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"'{oid}' is not a valid {label}.",
        )


async def _populate_ticket(doc: dict, db) -> HelpTicketResponse:
    """
    Populate customer field — fetch name and phone_number from customers collection.
    """
    populated_customer = None
    if doc.get("customer"):
        try:
            customer_doc = await db["customers"].find_one({"_id": ObjectId(doc["customer"])})
            if customer_doc:
                populated_customer = PopulatedTicketCustomer(
                    customer_id=customer_doc.get("customer_id"),
                    name=customer_doc.get("name"),
                    phone_number=customer_doc.get("phone_number"),
                )
        except Exception:
            pass

    return HelpTicketResponse(
        id=str(doc["_id"]),
        ticket_id=doc["ticket_id"],
        customer=populated_customer,
        issue=doc.get("issue"),
        status=doc.get("status"),
        priority=doc.get("priority"),
        category=doc.get("category"),
        assigned_agent=doc.get("assigned_agent"),
        source=doc.get("source"),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


class HelpTicketController:

    @staticmethod
    async def create_ticket(data: HelpTicketCreate, db) -> HelpTicketResponse:
        """Create a new help ticket."""

        
        if data.customer:
            _validate_object_id(data.customer, "customer ID")
            customer_exists = await db["customers"].find_one({"_id": ObjectId(data.customer)})
            if not customer_exists:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Customer not found.",
                )

        now = datetime.now(timezone.utc)
        ticket_doc = {
            "ticket_id": f"TKT-{uuid4().hex[:8].upper()}",     
            "status": data.status.value if data.status else TicketStatus.OPEN.value,
            "priority": data.priority.value if data.priority else TicketPriority.LOW.value,
            "source": data.source.value if data.source else TicketSource.MANUAL.value,
            "created_at": now,
            "updated_at": now,
            # only store fields that were actually sent
            **{k: v for k, v in data.model_dump(exclude_none=True).items()
               if k not in {"status", "priority", "source"}},
        }

        result = await db["help_tickets"].insert_one(ticket_doc)
        ticket_doc["_id"] = result.inserted_id
        return await _populate_ticket(ticket_doc, db)

    @staticmethod
    async def fetch_all_tickets(db) -> list[HelpTicketResponse]:
        """Return all help tickets unpaginated."""
        tickets = await db["help_tickets"].find().sort("created_at", -1).to_list(length=None)
        return [await _populate_ticket(t, db) for t in tickets]

    @staticmethod
    async def get_paginated_tickets(db, page: int = 1, limit: int = 10) -> PaginatedHelpTicketResponse:
        """Return a paginated list of help tickets."""
        skip = (page - 1) * limit

        total_results = await db["help_tickets"].count_documents({})
        tickets = await db["help_tickets"].find().skip(skip).limit(limit).sort("created_at", -1).to_list(length=None)
        total_pages = math.ceil(total_results / limit)

        return PaginatedHelpTicketResponse(
            total_results=total_results,
            page=page,
            limit=limit,
            total_pages=total_pages,
            data=[await _populate_ticket(t, db) for t in tickets],
        )

    @staticmethod
    async def get_ticket(ticket_id: str, db) -> HelpTicketResponse:
        """Fetch a single help ticket by ID — customer is populated."""
        _validate_object_id(ticket_id, "ticket ID")

        ticket = await db["help_tickets"].find_one({"_id": ObjectId(ticket_id)})
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Help ticket not found.",
            )
        return await _populate_ticket(ticket, db)

    @staticmethod
    async def update_ticket(ticket_id: str, data: HelpTicketUpdate, db) -> HelpTicketResponse:
        """Partial update — only the fields provided in the request body are changed."""
        _validate_object_id(ticket_id, "ticket ID")

        existing = await db["help_tickets"].find_one({"_id": ObjectId(ticket_id)})
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Help ticket not found.",
            )

        update_fields = data.model_dump(exclude_none=True)
        if not update_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields provided to update.",
            )

        # validate customer ObjectId if being updated
        if "customer" in update_fields:
            _validate_object_id(update_fields["customer"], "customer ID")
            customer_exists = await db["customers"].find_one({"_id": ObjectId(update_fields["customer"])})
            if not customer_exists:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Customer not found.",
                )

        # convert enums to values
        for field in ["status", "priority", "source"]:
            if field in update_fields and hasattr(update_fields[field], "value"):
                update_fields[field] = update_fields[field].value

        update_fields["updated_at"] = datetime.now(timezone.utc)
        await db["help_tickets"].update_one(
            {"_id": ObjectId(ticket_id)},
            {"$set": update_fields},
        )

        updated = await db["help_tickets"].find_one({"_id": ObjectId(ticket_id)})
        return await _populate_ticket(updated, db)

    @staticmethod
    async def delete_ticket(ticket_id: str, db) -> dict:
        """Hard-delete a help ticket."""
        _validate_object_id(ticket_id, "ticket ID")

        result = await db["help_tickets"].delete_one({"_id": ObjectId(ticket_id)})
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Help ticket not found.",
            )
        return {"deleted_id": ticket_id}