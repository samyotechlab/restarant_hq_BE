import math
from datetime import datetime, timezone
from uuid import uuid4
from bson import ObjectId
from fastapi import HTTPException, status

from models.orders_model import (
    OrderCreate,
    OrderResponse,
    OrderUpdate,
    OrderStatus,
    PaymentMethod,
    OrderItemResponse,
    PopulatedCustomer,
    PaginatedOrderResponse,
)


def _validate_object_id(oid: str, label: str = "ID") -> None:
    """Raise a 400 early if the provided ID is not a valid MongoDB ObjectId."""
    if not ObjectId.is_valid(oid):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"'{oid}' is not a valid {label}.",
        )


async def _populate_order(doc: dict, db) -> OrderResponse:
    """
    Manually populate customer and menu_items in an order document.
    
    MongoDB Motor doesn't have built-in populate like Mongoose.
    So we:
    1. Fetch the customer doc using the stored customer ObjectId
    2. For each item in the order, fetch the menu_item doc using its ObjectId
    3. Embed the fetched data into the response
    """

    
    populated_customer = None
    if doc.get("customer"):
        customer_doc = await db["customers"].find_one({"_id": ObjectId(doc["customer"])})
        if customer_doc:
            populated_customer = PopulatedCustomer(
                customer_id=customer_doc.get("customer_id"),
                name=customer_doc.get("name"),
                phone_number=customer_doc.get("phone_number"),
                email=customer_doc.get("email"),
            )

    
    populated_items = []
    for item in doc.get("items", []):
        menu_doc = await db["menu_items"].find_one({"_id": ObjectId(item["menu_item"])})
        populated_items.append(OrderItemResponse(
            menu_item_id=item["menu_item"],
            item_no=menu_doc.get("item_no") if menu_doc else None,
            item_name=menu_doc.get("item_name") if menu_doc else None,
            image=menu_doc.get("image") if menu_doc else None,
            category=menu_doc.get("category") if menu_doc else None,
            price=item.get("price"),
            quantity=item.get("quantity"),
            sub_total=item.get("sub_total"),
        ))

    return OrderResponse(
        id=str(doc["_id"]),
        order_id=doc["order_id"],
        customer=populated_customer,
        items=populated_items,
        status=doc["status"],
        sub_total=doc.get("sub_total"),
        tax=doc.get("tax"),
        discount=doc.get("discount"),
        grand_total=doc.get("grand_total"),
        notes=doc.get("notes"),
        payment_method=doc["payment_method"],
        is_paid=doc["is_paid"],
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


class OrderController:

    @staticmethod
    async def create_order(data: OrderCreate, db) -> OrderResponse:
        """Create a new order."""

        
        if data.customer:
            _validate_object_id(data.customer, "customer ID")
            customer_exists = await db["customers"].find_one({"_id": ObjectId(data.customer)})
            if not customer_exists:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Customer not found.",
                )


        items_to_store = []
        for item in (data.items or []):
            _validate_object_id(item.menu_item, "menu item ID")
            menu_exists = await db["menu_items"].find_one({"_id": ObjectId(item.menu_item)})
            if not menu_exists:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Menu item '{item.menu_item}' not found.",
                )
            items_to_store.append({
                "menu_item": item.menu_item,    
                "price": item.price,
                "quantity": item.quantity,
                "sub_total": item.sub_total,
            })

        now = datetime.now(timezone.utc)
        order_doc = {
            "order_id": f"ORD-{uuid4().hex[:8].upper()}",      
            "customer": data.customer,
            "items": items_to_store,
            "status": data.status.value if data.status else OrderStatus.PENDING.value,
            "sub_total": data.sub_total,
            "tax": data.tax,
            "discount": data.discount,
            "grand_total": data.grand_total,
            "notes": data.notes,
            "payment_method": data.payment_method.value if data.payment_method else PaymentMethod.PENDING.value,
            "is_paid": data.is_paid if data.is_paid is not None else False,
            "created_at": now,
            "updated_at": now,
        }

        result = await db["orders"].insert_one(order_doc)
        order_doc["_id"] = result.inserted_id

       
        if data.customer:
            await db["customers"].update_one(
                {"_id": ObjectId(data.customer)},
                {
                    "$addToSet": {"orders": str(result.inserted_id)},
                    "$set": {"updated_at": datetime.now(timezone.utc)},
                },
            )

        return await _populate_order(order_doc, db)

    @staticmethod
    async def get_order(order_id: str, db) -> OrderResponse:
        """Fetch a single order by ID — customer and items are populated."""
        _validate_object_id(order_id, "order ID")

        order = await db["orders"].find_one({"_id": ObjectId(order_id)})
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found.",
            )
        return await _populate_order(order, db)

    @staticmethod
    async def get_all_orders(db) -> list[OrderResponse]:
        """Return all orders — unpaginated, unauthenticated."""
        orders = await db["orders"].find().to_list(length=None)
        return [await _populate_order(o, db) for o in orders]

    @staticmethod
    async def get_all_orders_paginated(db, page: int = 1, limit: int = 10) -> PaginatedOrderResponse:
        """Return a paginated list of orders."""
        skip = (page - 1) * limit

        total_results = await db["orders"].count_documents({})
        orders = await db["orders"].find().skip(skip).limit(limit).to_list(length=None)
        total_pages = math.ceil(total_results / limit)

        return PaginatedOrderResponse(
            total_results=total_results,
            page=page,
            limit=limit,
            total_pages=total_pages,
            data=[await _populate_order(o, db) for o in orders],
        )

    @staticmethod
    async def update_order(order_id: str, data: OrderUpdate, db) -> OrderResponse:
        """Partial update — only the fields provided in the request body are changed."""
        _validate_object_id(order_id, "order ID")

        existing = await db["orders"].find_one({"_id": ObjectId(order_id)})
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found.",
            )

        update_fields = data.model_dump(exclude_none=True)
        if not update_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields provided to update.",
            )

        
        if "items" in update_fields:
            items_to_store = []
            for item in update_fields["items"]:
                _validate_object_id(item["menu_item"], "menu item ID")
                items_to_store.append({
                    "menu_item": item["menu_item"],
                    "price": item.get("price"),
                    "quantity": item.get("quantity"),
                    "sub_total": item.get("sub_total"),
                })
            update_fields["items"] = items_to_store

        # convert enums to their values
        if "status" in update_fields:
            update_fields["status"] = update_fields["status"].value if hasattr(update_fields["status"], "value") else update_fields["status"]
        if "payment_method" in update_fields:
            update_fields["payment_method"] = update_fields["payment_method"].value if hasattr(update_fields["payment_method"], "value") else update_fields["payment_method"]

        update_fields["updated_at"] = datetime.now(timezone.utc)
        await db["orders"].update_one(
            {"_id": ObjectId(order_id)},
            {"$set": update_fields},
        )

        updated = await db["orders"].find_one({"_id": ObjectId(order_id)})
        return await _populate_order(updated, db)

    @staticmethod
    async def delete_order(order_id: str, db) -> dict:
        """Hard-delete an order."""
        _validate_object_id(order_id, "order ID")

        result = await db["orders"].delete_one({"_id": ObjectId(order_id)})
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found.",
            )
        return {"deleted_id": order_id}