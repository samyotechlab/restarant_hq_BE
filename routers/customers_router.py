from typing import List

from fastapi import APIRouter, Depends, status, Query
from auth.dependencies import get_current_user                                  
from db.database import get_db
from models.customers_model import CustomerCreate, CustomerResponse, CustomerUpdate, BulkUploadResponse, PaginatedCustomerResponse
from models.base_model import StandardResponse
from controller.customers_controller import CustomerController, _to_response

router = APIRouter(prefix="/customers", tags=["Customers"])


@router.post(
    "/",
    response_model=StandardResponse[CustomerResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new customer",
    include_in_schema=False
)
async def create_customer(
    data: CustomerCreate,
    db=Depends(get_db),
    # _: dict = Depends(get_current_user),                                 
):
    """
    Register a new customer.
    Rejects duplicate emails with a 400 error.
    """
    result = await CustomerController.create_customer(data, db)
    return StandardResponse(
        status_code=status.HTTP_201_CREATED,
        message="Customer Created Successfully",
        result_data=result,
    )


@router.get(
    "/",
    response_model=StandardResponse[PaginatedCustomerResponse],
    summary="Get all customers with pagination",
)
async def get_all_customers_paginated(
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=10, ge=1, le=1000, description="Items per page"),
    db=Depends(get_db),
    _: dict = Depends(get_current_user),                                        
):
    """Return a paginated list of customers. Defaults to page 1 with 10 items."""
    result = await CustomerController.get_all_customers_paginated(db, page, limit)
    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="Customers Fetched Successfully",
        result_data=result,
    )


@router.get(
    "/fetch_all",
    response_model=StandardResponse[List[CustomerResponse]],
    summary="Get all customers",
    include_in_schema=False
)
async def get_all_customers(db=Depends(get_db)):
    """Return all the customers"""
    result = await CustomerController.get_all_customers(db)
    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="Customers Fetched Successfully",
        result_data=result,
    )


@router.get(
    "/search",
    response_model=StandardResponse[CustomerResponse],
    summary="Get a single customer by Phone Number",
    include_in_schema=False
)
async def get_customer_by_phone(
    phone: str = Query(..., description="The phone number of the customer"),
    db=Depends(get_db),
):
    """Fetch one customer by their phone number. Returns 404 if not found."""
    result = await CustomerController.get_customer_by_phone(phone, db)
    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="Customer Fetched Successfully",
        result_data=result,
    )


@router.get(
    "/{customer_id}",
    response_model=StandardResponse[CustomerResponse],
    summary="Get a single customer by ID",
)
async def get_customer(
    customer_id: str,
    db=Depends(get_db),
    # _: dict = Depends(get_current_user),                                      
):
    """Fetch one customer by their ID. Returns 404 if not found."""
    result = await CustomerController.get_customer(customer_id, db)
    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="Customer Fetched Successfully",
        result_data=result,
    )


@router.patch(
    "/{customer_id}",
    response_model=StandardResponse[CustomerResponse],
    summary="Partially update a customer",
    include_in_schema=False
)
async def update_customer(
    customer_id: str,
    data: CustomerUpdate,
    db=Depends(get_db),
    # _: dict = Depends(get_current_user),                                     
):
    """
    Update one or more fields of a customer.
    Only fields included in the request body are changed.
    """
    result = await CustomerController.update_customer(customer_id, data, db)
    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="Customer Updated Successfully",
        result_data=result,
    )


@router.delete(
    "/{customer_id}",
    response_model=StandardResponse[dict],
    summary="Delete a customer",
)
async def delete_customer(
    customer_id: str,
    db=Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """Hard-delete a customer. Returns the deleted customer's ID."""
    result = await CustomerController.delete_customer(customer_id, db)
    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="Customer Deleted Successfully",
        result_data=result,
    )


@router.post(
    "/{customer_id}/orders/{order_id}",
    response_model=StandardResponse[CustomerResponse],
    summary="Link an order to a customer",
)
async def add_order_to_customer(
    customer_id: str,
    order_id: str,
    db=Depends(get_db),
    _: dict = Depends(get_current_user),                                        
):
    """
    Attach an order ID to the customer's orders list.
    Duplicate order IDs are automatically ignored.
    """
    result = await CustomerController.add_order(customer_id, order_id, db)
    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="Order Linked Successfully",
        result_data=result,
    )


@router.post(
    "/bulk_upload",
    response_model=StandardResponse[BulkUploadResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Bulk upload customers via array of objects",
)
async def bulk_upload_customers(
    data: list[CustomerCreate],
    db=Depends(get_db),
    _: dict = Depends(get_current_user),                                       
):
    """
    Upload multiple customers in one request as a JSON array.
    Failed entries are skipped and reported individually in the response.
    """
    result = await CustomerController.bulk_create_customers(data, db)
    return StandardResponse(
        status_code=status.HTTP_201_CREATED,
        message="Bulk Upload Completed",
        result_data=result,
    )