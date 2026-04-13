import math
from datetime import datetime, timezone
import os
from uuid import uuid4
from bson import ObjectId
from fastapi import BackgroundTasks, HTTPException, UploadFile, status
from helpers.order_bulk_upload_helper import (
    _process_bulk_upload_job,
)
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

UPLOAD_DIR_ORDERS = "uploads/orders"
PROGRESS_EVERY = 50

def _validate_object_id(oid: str, label: str = "ID") -> None:
    """Raise a 400 early if the provided ID is not a valid MongoDB ObjectId."""
    if not ObjectId.is_valid(oid):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"'{oid}' is not a valid {label}.",
        )


async def _populate_order(doc: dict, db) -> OrderResponse:
    populated_customer = None
    raw_customer = doc.get("customer")
    if raw_customer:
        try:
            customer_doc = await db["customers"].find_one(
                {"_id": ObjectId(str(raw_customer))}
            )
            if customer_doc:
                populated_customer = PopulatedCustomer(
                    customer_id=str(customer_doc["_id"]),
                    name=customer_doc.get("name"),
                    country_code=customer_doc.get("country_code"),
                    phone_number=customer_doc.get("phone_number"),
                    address=customer_doc.get("address"),
                )
        except Exception:
            pass

    populated_items = []
    for item in doc.get("items", []):
        menu_doc = None
        raw_menu_id = item.get("menu_item")
        if raw_menu_id and ObjectId.is_valid(str(raw_menu_id)):
            try:
                menu_doc = await db["menu_items"].find_one(
                    {"_id": ObjectId(str(raw_menu_id))}
                )
            except Exception:
                menu_doc = None

        populated_items.append(OrderItemResponse(
            menu_item_id=str(raw_menu_id) if raw_menu_id else None,
            item_no=menu_doc.get("item_no") if menu_doc else None,
            item_name=menu_doc.get("item_name") if menu_doc else item.get("item_name"),
            image=menu_doc.get("image") if menu_doc else None,
            category=menu_doc.get("category") if menu_doc else item.get("category"),
            base_price=menu_doc.get("base_price") if menu_doc else None,
            online_price=menu_doc.get("online_price") if menu_doc else None,
            dietary=menu_doc.get("dietary") if menu_doc else None,
            available=menu_doc.get("available") if menu_doc else None,
            price=item.get("price"),
            quantity=item.get("quantity"),
            sub_total=item.get("sub_total"),
            final_total=item.get("final_total"),
        ))

    return OrderResponse(
        id=str(doc["_id"]),
        order_id=doc["order_id"],
        invoice_no=doc.get("invoice_no"),
        order_date=doc.get("order_date"),
        order_timestamp=doc.get("order_timestamp"),
        order_type=doc.get("order_type"),
        area=doc.get("area"),
        table_no=doc.get("table_no"),
        covers=doc.get("covers"),
        server_name=doc.get("server_name"),
        assign_to=doc.get("assign_to"),
        customer=populated_customer,
        items=populated_items,
        status=doc["status"],
        sub_total=doc.get("sub_total"),
        tax=doc.get("tax"),
        discount=doc.get("discount"),
        grand_total=doc.get("grand_total"),
        vat_amount=doc.get("vat_amount"),
        non_taxable=doc.get("non_taxable"),
        gst=doc.get("gst"),
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
        """Fetch a single order by order_id (e.g. ORD-3F9A1B2C)."""
        order = await db["orders"].find_one({"order_id": order_id})
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found.",
            )
        return await _populate_order(order, db)

    @staticmethod
    async def get_all_orders(db) -> list[OrderResponse]:
        """Return all orders — unpaginated, unauthenticated."""
        orders = await db["orders"].find().sort('created_at', -1).to_list(length=None)
        return [await _populate_order(o, db) for o in orders]

    @staticmethod
    async def get_all_orders_paginated(db, page: int = 1, limit: int = 10) -> PaginatedOrderResponse:
        """Return a paginated list of orders."""
        skip = (page - 1) * limit

        total_results = await db["orders"].count_documents({})
        orders = await db["orders"].find().skip(skip).limit(limit).sort('created_at', -1).to_list(length=None)
        total_pages = math.ceil(total_results / limit) if total_results else 1

        return PaginatedOrderResponse(
            total_results=total_results,
            page=page,
            limit=limit,
            total_pages=total_pages,
            data=[await _populate_order(o, db) for o in orders],
        )

    @staticmethod
    async def get_orders_by_phone(db, phone: str, limit: int = 3) -> list[OrderResponse]:
        """
        Fetch last N orders for a customer identified by phone number.
        Used by the AI agent to recall order history.
        """
        customer = await db["customers"].find_one({"phone_number": {"$regex": phone, "$options": "i"}})
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No customer found with phone number '{phone}'.",
            )

        orders = await db["orders"].find({"customer": customer["_id"]}).sort("created_at", -1).limit(limit).to_list(length=limit)
        if not orders:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No orders found for phone '{phone}'.",
            )

        return [await _populate_order(o, db) for o in orders]

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
    async def bulk_upload_orders(
        background_tasks: BackgroundTasks,
        file: UploadFile,
        db,
    ) -> dict:
        if not file.filename or not file.filename.endswith((".csv", ".xlsx", ".xls")):
            raise HTTPException(status_code=400, detail="Only CSV or Excel files allowed.")

        os.makedirs(UPLOAD_DIR_ORDERS, exist_ok=True)
        job_id = str(uuid4())
        file_path = f"{UPLOAD_DIR_ORDERS}/{job_id}_{file.filename}"

        with open(file_path, "wb") as f:
            while chunk := await file.read(1024 * 1024):
                f.write(chunk)

        await db["order_bulk_jobs"].insert_one({
            "job_id": job_id,
            "file_name": file.filename,
            "file_path": file_path,
            "status": "queued",
            "total_invoices": 0,
            "processed_invoices": 0,
            "customers_created": 0,
            "customers_found": 0,
            "orders_created": 0,
            "skipped_no_phone": 0,
            "items_not_found": [],
            "errors": [],
            "started_at": None,
            "completed_at": None,
            "created_at": datetime.now(timezone.utc),
        })

        background_tasks.add_task(_process_bulk_upload_job, job_id, file_path, db)

        return {
            "status_code": 202,
            "message": "Orders file uploaded. Processing in background.",
            "result_data": {
                "job_id": job_id,
                "file_name": file.filename,
            },
        }

    @staticmethod
    async def get_bulk_upload_status(job_id: str, db) -> dict:
        job = await db["order_bulk_jobs"].find_one({"job_id": job_id}, {"_id": 0})
        if not job:
            raise HTTPException(status_code=404, detail="Bulk upload job not found.")

        total = job.get("total_invoices") or 1
        processed = job.get("processed_invoices", 0)

        return {
            "status_code": 200,
            "message": "Job status fetched",
            "result_data": {
                "job_id": job["job_id"],
                "file_name": job["file_name"],
                "status": job["status"],
                "total_invoices": job.get("total_invoices", 0),
                "processed_invoices": processed,
                "progress_percent": round((processed / total) * 100, 2),
                "customers_created": job.get("customers_created", 0),
                "customers_found": job.get("customers_found", 0),
                "orders_created": job.get("orders_created", 0),
                "orders_updated": job.get("orders_updated", 0),
                "skipped_no_phone": job.get("skipped_no_phone", 0),
                "items_not_found": job.get("items_not_found", []),
                "errors": job.get("errors", []),
                "started_at": job.get("started_at"),
                "completed_at": job.get("completed_at"),
                "created_at": job.get("created_at"),
            },
        }
    
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