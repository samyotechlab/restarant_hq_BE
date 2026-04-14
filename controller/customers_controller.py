import math
from datetime import datetime, timezone
from typing import List
from uuid import uuid4
from bson import ObjectId
from fastapi import HTTPException, status

from models.customers_model import (
    CustomerCreate,
    CustomerResponse,
    CustomerUpdate,
    CustomerStatus,
    BulkUploadResult,
    BulkUploadResponse,
    PaginatedCustomerResponse,
    PopulatedOrder,
)

async def _to_response(doc: dict, db) -> CustomerResponse:
    """Convert a single customer document to CustomerResponse."""
    populated_orders = []
    order_ids = []
    for oid in doc.get("orders", []):
        try:
            if ObjectId.is_valid(str(oid)):
                order_ids.append(ObjectId(str(oid)))
        except Exception:
            continue

    if order_ids:
        order_docs = await db["orders"].find(
            {"_id": {"$in": order_ids}}
        ).to_list(length=None)
    else:
        order_docs = []

    for order_doc in order_docs:
        try:
            menu_ids = []
            for item in order_doc.get("items", []):
                raw_mid = item.get("menu_item")
                if raw_mid and ObjectId.is_valid(str(raw_mid)):
                    menu_ids.append(ObjectId(str(raw_mid)))

            menu_map = {}
            if menu_ids:
                menu_docs = await db["menu_items"].find(
                    {"_id": {"$in": menu_ids}}
                ).to_list(length=None)
                menu_map = {str(m["_id"]): m for m in menu_docs}

            from models.orders_model import OrderItemResponse
            formatted_items = []
            for item in order_doc.get("items", []):
                raw_mid = item.get("menu_item")
                menu_doc = menu_map.get(str(raw_mid)) if raw_mid else None

                formatted_items.append(OrderItemResponse(
                    menu_item_id=str(raw_mid) if raw_mid else None,
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

            populated_orders.append(PopulatedOrder(
                id=str(order_doc["_id"]),
                order_id=order_doc.get("order_id"),
                grand_total=order_doc.get("grand_total"),
                items=formatted_items,
            ))

        except Exception as e:
            print(f"Error populating order {order_doc.get('_id')}: {e}")
            continue

    order_docs_sorted = sorted(
        order_docs,
        key=lambda o: o.get("order_date") or o.get("created_at") or datetime.min.replace(tzinfo=timezone.utc),  # ← order_date
        reverse=True
    )
    last_order_at = order_docs_sorted[0].get("order_date") if order_docs_sorted else None
    return CustomerResponse(
        id=str(doc["_id"]),
        customer_id=doc.get("customer_id") or str(doc.get("_id", "")),
        name=doc.get("name", "Unknown"),
        country_code=doc.get("country_code"),
        phone_number=doc.get("phone_number", ""),
        email=doc.get("email"),
        address=doc.get("address"),
        orders=populated_orders,
        status=doc.get("status", "new").lower(),
        last_order_at=last_order_at,
        created_at=doc.get("created_at", datetime.now(timezone.utc)),
        updated_at=doc.get("updated_at", datetime.now(timezone.utc)),
    )


async def _build_responses_optimized(customers: list[dict], db) -> List[CustomerResponse]:
    """
    Optimized batch conversion of multiple customers to responses.
    Batches all order and menu item queries instead of individual lookups per customer.
    """
    # Step 1: Collect all order IDs from all customers
    all_order_ids = set()
    customer_order_map = {}  # Maps customer index to their order IDs
    
    for idx, customer in enumerate(customers):
        customer_orders = []
        for oid in customer.get("orders", []):
            try:
                if ObjectId.is_valid(str(oid)):
                    oid_obj = ObjectId(str(oid))
                    all_order_ids.add(oid_obj)
                    customer_orders.append(oid_obj)
            except Exception:
                continue
        customer_order_map[idx] = customer_orders
    
    # Step 2: Fetch all orders in one query
    all_order_ids_list = list(all_order_ids)
    order_map = {}
    if all_order_ids_list:
        order_docs = await db["orders"].find(
            {"_id": {"$in": all_order_ids_list}}
        ).to_list(length=None)
        order_map = {str(doc["_id"]): doc for doc in order_docs}
    
    # Step 3: Collect all menu IDs from all orders
    all_menu_ids = set()
    for order_doc in order_map.values():
        for item in order_doc.get("items", []):
            raw_mid = item.get("menu_item")
            if raw_mid and ObjectId.is_valid(str(raw_mid)):
                all_menu_ids.add(ObjectId(str(raw_mid)))
    
    # Step 4: Fetch all menu items in one query
    menu_map = {}
    if all_menu_ids:
        menu_docs = await db["menu_items"].find(
            {"_id": {"$in": list(all_menu_ids)}}
        ).to_list(length=None)
        menu_map = {str(m["_id"]): m for m in menu_docs}
    
    # Step 5: Build responses in memory
    responses = []
    for idx, customer_doc in enumerate(customers):
        populated_orders = []
        
        for order_id in customer_order_map.get(idx, []):
            try:
                order_doc = order_map.get(str(order_id))
                if not order_doc:
                    continue
                
                from models.orders_model import OrderItemResponse
                formatted_items = []
                for item in order_doc.get("items", []):
                    raw_mid = item.get("menu_item")
                    menu_doc = menu_map.get(str(raw_mid)) if raw_mid else None
                    
                    formatted_items.append(OrderItemResponse(
                        menu_item_id=str(raw_mid) if raw_mid else None,
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
                
                populated_orders.append(PopulatedOrder(
                    id=str(order_doc["_id"]),
                    order_id=order_doc.get("order_id"),
                    grand_total=order_doc.get("grand_total"),
                    items=formatted_items,
                ))
                
            except Exception as e:
                print(f"Error populating order {order_id}: {e}")
                continue
        customer_order_docs = [
            order_map[str(oid)]
            for oid in customer_order_map.get(idx, [])
            if str(oid) in order_map
        ]
        last_order_at = None
        if customer_order_docs:
            latest = max(
                customer_order_docs,
                key=lambda o: o.get("order_date") or o.get("created_at") or datetime.min.replace(tzinfo=timezone.utc)
            )
            last_order_at = latest.get("order_date") or latest.get("created_at")
        response = CustomerResponse(
            id=str(customer_doc["_id"]),
            customer_id=customer_doc.get("customer_id") or str(customer_doc.get("_id", "")),
            name=customer_doc.get("name", "Unknown"),
            country_code=customer_doc.get("country_code"),
            phone_number=customer_doc.get("phone_number", ""),
            email=customer_doc.get("email"),
            address=customer_doc.get("address"),
            orders=populated_orders,
            status=customer_doc.get("status", "new").lower(),
            last_order_at=last_order_at,
            created_at=customer_doc.get("created_at", datetime.now(timezone.utc)),
            updated_at=customer_doc.get("updated_at", datetime.now(timezone.utc)),
        )
        responses.append(response)
    
    return responses


def _validate_object_id(customer_id: str) -> None:
    """Raise a 400 early if the provided ID is not a valid MongoDB ObjectId."""
    if not ObjectId.is_valid(customer_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"'{customer_id}' is not a valid customer ID.",
        )


class CustomerController:

    @staticmethod
    async def create_customer(data: CustomerCreate, db) -> CustomerResponse:
        """Register a brand-new customer. Rejects duplicate emails if provided."""

        if data.email:
            existing = await db["customers"].find_one({"email": data.email})
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A customer with this email already exists.",
                )

        now = datetime.now(timezone.utc)
        customer_doc = data.model_dump()
    
        customer_doc.update({
            "customer_id": f"CUS-{uuid4().hex[:8].upper()}",
            "orders": [],
            "status": data.status.value,
            "created_at": now,
            "updated_at": now,
        })

        result = await db["customers"].insert_one(customer_doc)
        customer_doc["_id"] = result.inserted_id
        return await _to_response(customer_doc, db)

    @staticmethod
    async def get_customer(customer_id: str, db) -> CustomerResponse:
        """Fetch one customer by ID."""
        _validate_object_id(customer_id)

        customer = await db["customers"].find_one({"_id": ObjectId(customer_id)})
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found.",
            )
        return await _to_response(customer, db)

    @staticmethod
    async def get_customer_by_phone(customer_phone: str, db) -> CustomerResponse:
        """Fetch one customer by phone number."""
        customer = await db["customers"].find_one({"phone_number": customer_phone})
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found.",
            )
        return await _to_response(customer, db)

    @staticmethod
    async def get_all_customers_paginated(db, page: int = 1, limit: int = 10) -> PaginatedCustomerResponse:
        """Return a paginated list of customers with optimized batch queries."""
        skip = (page - 1) * limit

        total_results = await db["customers"].count_documents({})
        customers = await db["customers"].find().skip(skip).limit(limit).sort('created_at', -1).to_list(length=None)
        total_pages = math.ceil(total_results / limit)

        # Use optimized batch processing for multiple customers
        data = await _build_responses_optimized(customers, db)

        return PaginatedCustomerResponse(
            total_results=total_results,
            page=page,
            limit=limit,
            total_pages=total_pages,
            data=data,
        )

    @staticmethod
    async def get_all_customers(db) -> List[CustomerResponse]:
        """Return all customers sorted by created_at with optimized batch queries."""
        customers = await db["customers"].find().sort("created_at", -1).to_list(length=None)
        # Use optimized batch processing for all customers
        return await _build_responses_optimized(customers, db)


    @staticmethod
    async def update_customer(customer_id: str, data: CustomerUpdate, db) -> CustomerResponse:
        """Partial update — only the fields provided in the request body are changed."""
        _validate_object_id(customer_id)

        existing = await db["customers"].find_one({"_id": ObjectId(customer_id)})
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found.",
            )

        update_fields = data.model_dump(exclude_none=True)
        if not update_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields provided to update.",
            )

        update_fields["updated_at"] = datetime.now(timezone.utc)
        await db["customers"].update_one(
            {"_id": ObjectId(customer_id)},
            {"$set": update_fields},
        )

        updated = await db["customers"].find_one({"_id": ObjectId(customer_id)})
        return await _to_response(updated, db)

    @staticmethod
    async def delete_customer(customer_id: str, db) -> dict:
        """Hard-delete a customer record."""
        _validate_object_id(customer_id)

        result = await db["customers"].delete_one({"_id": ObjectId(customer_id)})
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found.",
            )
        return {"deleted_id": customer_id}

    @staticmethod
    async def add_order(customer_id: str, order_id: str, db) -> CustomerResponse:
        """Link an order ID to a customer's orders list."""
        _validate_object_id(customer_id)

        existing = await db["customers"].find_one({"_id": ObjectId(customer_id)})
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found.",
            )

        await db["customers"].update_one(
            {"_id": ObjectId(customer_id)},
            {
                "$addToSet": {"orders": order_id},
                "$set": {"updated_at": datetime.now(timezone.utc)},
            },
        )

        updated = await db["customers"].find_one({"_id": ObjectId(customer_id)})
        return await _to_response(updated, db)

    @staticmethod
    async def bulk_create_customers(data: list[CustomerCreate], db) -> BulkUploadResponse:
        """
        Insert multiple customers from a JSON array.
        Skips failed entries and reports them individually.
        """
        results = []
        inserted = 0
        failed = 0

        for index, customer in enumerate(data):
            try:
                existing = await db["customers"].find_one({"email": customer.email})
                if existing:
                    raise ValueError(f"Email '{customer.email}' already exists.")

                now = datetime.now(timezone.utc)
                customer_doc = {
                    "customer_id": f"CUS-{uuid4().hex[:8].upper()}",
                    "name": customer.name,
                    "country_code": customer.country_code,
                    "phone_number": customer.phone_number,
                    "email": customer.email,
                    "address": customer.address,
                    "orders": [],
                    "status": customer.status.value if hasattr(customer.status, "value") else customer.status,
                    "created_at": now,
                    "updated_at": now,
                }

                result = await db["customers"].insert_one(customer_doc)
                customer_doc["_id"] = result.inserted_id

                results.append(BulkUploadResult(
                    index=index,
                    success=True,
                    customer=await _to_response(customer_doc, db),
                ))
                inserted += 1

            except Exception as e:
                results.append(BulkUploadResult(
                    index=index,
                    success=False,
                    error=str(e),
                ))
                failed += 1

        return BulkUploadResponse(
            total=len(data),
            inserted=inserted,
            failed=failed,
            results=results,
        )

    @staticmethod
    async def bulk_create_from_csv(file_bytes: bytes, db) -> BulkUploadResponse:
        """
        Parse a CSV file and bulk insert customers.
        Expected CSV columns (header row required):
        name, country_code, phone_number, email, address
        """
        import csv
        import io

        content = file_bytes.decode("utf-8")
        reader = csv.DictReader(io.StringIO(content))

        required_columns = {"name", "country_code", "phone_number", "email", "address"}
        if not required_columns.issubset(set(reader.fieldnames or [])):
            missing = required_columns - set(reader.fieldnames or [])
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"CSV is missing required columns: {', '.join(missing)}",
            )

        customers = []
        for row in reader:
            try:
                customer = CustomerCreate(
                    name=row["name"].strip(),
                    country_code=row["country_code"].strip(),
                    phone_number=row["phone_number"].strip(),
                    email=row["email"].strip(),
                    address=row["address"].strip(),
                )
                customers.append(customer)
            except Exception:
                customers.append(None)

        results = []
        valid_customers = []
        for index, customer in enumerate(customers):
            if customer is None:
                results.append(BulkUploadResult(
                    index=index,
                    success=False,
                    error="Row data is invalid or missing required fields.",
                ))
            else:
                valid_customers.append((index, customer))

        
        inserted = 0
        failed = len(results)

        for index, customer in valid_customers:
            try:
                existing = await db["customers"].find_one({"email": customer.email})
                if existing:
                    raise ValueError(f"Email '{customer.email}' already exists.")

                now = datetime.now(timezone.utc)
                customer_doc = {
                    "customer_id": f"CUS-{uuid4().hex[:8].upper()}",
                    "name": customer.name,
                    "country_code": customer.country_code,
                    "phone_number": customer.phone_number,
                    "email": customer.email,
                    "address": customer.address,
                    "orders": [],
                    "status": CustomerStatus.NEW.value,
                    "created_at": now,
                    "updated_at": now,
                }

                result = await db["customers"].insert_one(customer_doc)
                customer_doc["_id"] = result.inserted_id

                results.append(BulkUploadResult(
                    index=index,
                    success=True,
                    customer=await _to_response(customer_doc, db),
                ))
                inserted += 1

            except Exception as e:
                results.append(BulkUploadResult(
                    index=index,
                    success=False,
                    error=str(e),
                ))
                failed += 1

        results.sort(key=lambda r: r.index)

        return BulkUploadResponse(
            total=len(customers),
            inserted=inserted,
            failed=failed,
            results=results,
        )