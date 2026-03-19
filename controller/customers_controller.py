import math
from datetime import datetime, timezone
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
    """
    Convert a raw MongoDB document into a CustomerResponse.
    Populates orders array — fetches each order and returns order_id + grand_total.
    """
    populated_orders = []
    for order_id_str in doc.get("orders", []):
        try:
            order_doc = await db["orders"].find_one({"_id": ObjectId(order_id_str)})
            if order_doc:
                populated_orders.append(PopulatedOrder(
                    order_id=str(order_doc["_id"]),
                    grand_total=order_doc.get("grand_total"),
                ))
        except Exception:
            continue

    return CustomerResponse(
        id=str(doc["_id"]),
        customer_id=doc["customer_id"],
        name=doc["name"],
        country_code=doc["country_code"],
        phone_number=doc["phone_number"],
        email=doc.get("email"),
        address=doc["address"],
        city=doc["city"],
        pincode=doc["pincode"],
        orders=populated_orders,
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
            "email": data.email,
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
    async def get_all_customers(db, page: int = 1, limit: int = 10) -> PaginatedCustomerResponse:
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
            data=[await _to_response(c, db) for c in customers],
        )

    @staticmethod
    async def get_all_customers(db) -> List[CustomerResponse]:
        """Return all customers sorted by created_at."""
        customers = await db["customers"].find().sort("created_at", -1).to_list(length=None)
        return [await _to_response(c, db) for c in customers]


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
                    "city": customer.city,
                    "pincode": customer.pincode,
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
        name, country_code, phone_number, email, address, city, pincode
        """
        import csv
        import io

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