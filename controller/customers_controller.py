import math
from datetime import datetime, timezone
from typing import List
from uuid import uuid4
from bson import ObjectId
from fastapi import HTTPException, status

from models.customers_model import CustomerCreate, CustomerResponse, CustomerUpdate, CustomerStatus, BulkUploadResult, BulkUploadResponse, PaginatedCustomerResponse


def _to_response(doc: dict) -> CustomerResponse:
    """Convert a raw MongoDB document into a CustomerResponse."""
    email = doc.get("email")
    if email is None:
        doc["email"] = None
    return CustomerResponse(
        id=str(doc["_id"]),
        customer_id=doc["customer_id"],
        name=doc["name"],
        country_code=doc["country_code"],
        phone_number=doc["phone_number"],
        email=doc["email"],
        address=doc["address"],
        city=doc["city"],
        pincode=doc["pincode"],
        orders=doc.get("orders", []),
        status=doc["status"],
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


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
        """Register a brand-new customer. Rejects duplicate emails."""
        if data.email:
            existing = await db["customers"].find_one({"email": data.email})
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A customer with this email already exists.",
                )

        now = datetime.now(timezone.utc)
        customer_doc = {
            "customer_id": f"CUS-{uuid4().hex[:8].upper()}",  
            "name": data.name,
            "country_code": data.country_code,
            "phone_number": data.phone_number,
            "email": data.email if data.email else None,
            "address": data.address,
            "city": data.city,
            "pincode": data.pincode,
            "orders": [],
            "status": CustomerStatus.NEW.value,
            "created_at": now,
            "updated_at": now,
        }

        result = await db["customers"].insert_one(customer_doc)
        customer_doc["_id"] = result.inserted_id
        return _to_response(customer_doc)

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
        return _to_response(customer)
    
    @staticmethod
    async def get_customer_by_phone(customer_phone: str, db) -> CustomerResponse:
        customer = await db["customers"].find_one({"phone_number": customer_phone});
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found.",
            )
        return _to_response(customer)

    @staticmethod
    async def get_all_customers_paginated(db, page: int = 1, limit: int = 10) -> PaginatedCustomerResponse:
        """Return a paginated list of customers."""
        skip = (page - 1) * limit

        total_results = await db["customers"].count_documents({})
        customers = await db["customers"].find().skip(skip).limit(limit).to_list(length=None)
        total_pages = math.ceil(total_results / limit)

        return PaginatedCustomerResponse(
            total_results=total_results,
            page=page,
            limit=limit,
            total_pages=total_pages,
            data=[_to_response(c) for c in customers],
        )
    
    @staticmethod
    async def get_all_customers(db) -> List[CustomerResponse]:
        customers = await db['customers'].find().sort("created_at", -1).to_list(length=None)
        return [_to_response(c) for c in customers]

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
        return _to_response(updated)

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
        return _to_response(updated)

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
                    "city": customer.city,
                    "pincode": customer.pincode,
                    "orders": [],
                    "status": customer.status,
                    "created_at": now,
                    "updated_at": now,
                }

                result = await db["customers"].insert_one(customer_doc)
                customer_doc["_id"] = result.inserted_id

                results.append(BulkUploadResult(
                    index=index,
                    success=True,
                    customer=_to_response(customer_doc),
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
        name, country_code, phone_number, email, address, city, pincode
        """
        import csv
        import io

        # decode bytes → string → CSV reader
        content = file_bytes.decode("utf-8")
        reader = csv.DictReader(io.StringIO(content))

        required_columns = {"name", "country_code", "phone_number", "email", "address", "city", "pincode"}
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
                    city=row["city"].strip(),
                    pincode=row["pincode"].strip(),
                )
                customers.append(customer)
            except Exception as e:
                customers.append(None)

        # separate valid and invalid rows before inserting
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
                    "city": customer.city,
                    "pincode": customer.pincode,
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
                    customer=_to_response(customer_doc),
                ))
                inserted += 1

            except Exception as e:
                results.append(BulkUploadResult(
                    index=index,
                    success=False,
                    error=str(e),
                ))
                failed += 1

        # sort results by original row index so response is in order
        results.sort(key=lambda r: r.index)

        return BulkUploadResponse(
            total=len(customers),
            inserted=inserted,
            failed=failed,
            results=results,
        )