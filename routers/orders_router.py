from fastapi import APIRouter, Depends, status, Query
from auth.dependencies import get_current_user
from db.database import get_db
from models.orders_model import OrderCreate, OrderResponse, OrderUpdate, PaginatedOrderResponse
from models.base_model import StandardResponse
from controller.orders_controller import OrderController

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post(
    "/",
    response_model=StandardResponse[OrderResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new order",
)
async def create_order(
    data: OrderCreate,
    db=Depends(get_db),
):
    """Create a new order. No authentication required."""
    result = await OrderController.create_order(data, db)
    return StandardResponse(
        status_code=status.HTTP_201_CREATED,
        message="Order Created Successfully",
        result_data=result,
    )


@router.get(
    "/fetch_all",
    response_model=StandardResponse[list[OrderResponse]],
    summary="Get all orders",
)
async def get_all_orders(
    db=Depends(get_db),
):
    """Return all orders without pagination. No authentication required."""
    result = await OrderController.get_all_orders(db)
    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="Orders Fetched Successfully",
        result_data=result,
    )


@router.get(
    "/",
    response_model=StandardResponse[PaginatedOrderResponse],
    summary="Get all orders with pagination",
)
async def get_all_orders_paginated(
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=10, ge=1, le=100, description="Items per page"),
    db=Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """Return a paginated list of orders."""
    result = await OrderController.get_all_orders_paginated(db, page, limit)
    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="Orders Fetched Successfully",
        result_data=result,
    )


@router.get(
    "/{order_id}",
    response_model=StandardResponse[OrderResponse],
    summary="Get a single order by ID",
)
async def get_order(
    order_id: str,
    db=Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """Fetch one order by its ID — customer and items are populated."""
    result = await OrderController.get_order(order_id, db)
    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="Order Fetched Successfully",
        result_data=result,
    )


@router.patch(
    "/{order_id}",
    response_model=StandardResponse[OrderResponse],
    summary="Partially update an order",
)
async def update_order(
    order_id: str,
    data: OrderUpdate,
    db=Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """Update one or more fields of an order."""
    result = await OrderController.update_order(order_id, data, db)
    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="Order Updated Successfully",
        result_data=result,
    )


@router.delete(
    "/{order_id}",
    response_model=StandardResponse[dict],
    summary="Delete an order",
)
async def delete_order(
    order_id: str,
    db=Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """Hard-delete an order."""
    result = await OrderController.delete_order(order_id, db)
    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="Order Deleted Successfully",
        result_data=result,
    )