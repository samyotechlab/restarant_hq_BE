from fastapi import APIRouter, Depends, status, Query
from auth.dependencies import get_current_user
from db.database import get_db
from models.services_model import ServiceCreate, ServiceResponse, ServiceUpdate, PaginatedServiceResponse
from models.base_model import StandardResponse
from controller.services_controller import ServiceController

router = APIRouter(prefix="/services", tags=["Services"])


@router.post(
    "/",
    response_model=StandardResponse[ServiceResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new service",
)
async def create_service(
    data: ServiceCreate,
    db=Depends(get_db),
    _: dict = Depends(get_current_user),                
):
    """Create a new service."""
    result = await ServiceController.create_service(data, db)
    return StandardResponse(
        status_code=status.HTTP_201_CREATED,
        message="Service Created Successfully",
        result_data=result,
    )


@router.get(
    "/",
    response_model=StandardResponse[PaginatedServiceResponse],
    summary="Get all services with pagination",
)
async def get_all_services(
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=10, ge=1, le=100, description="Items per page"),
    db=Depends(get_db),
    # no auth on get all
):
    """Return a paginated list of services. No authentication required."""
    result = await ServiceController.get_all_services(db, page, limit)
    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="Services Fetched Successfully",
        result_data=result,
    )


@router.patch(
    "/{service_id}",
    response_model=StandardResponse[ServiceResponse],
    summary="Partially update a service",
)
async def update_service(
    service_id: str,
    data: ServiceUpdate,
    db=Depends(get_db),
    _: dict = Depends(get_current_user),                
):
    """Update one or more fields of a service."""
    result = await ServiceController.update_service(service_id, data, db)
    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="Service Updated Successfully",
        result_data=result,
    )


@router.delete(
    "/{service_id}",
    response_model=StandardResponse[dict],
    summary="Delete a service",
)
async def delete_service(
    service_id: str,
    db=Depends(get_db),
    _: dict = Depends(get_current_user),                
):
    """Hard-delete a service."""
    result = await ServiceController.delete_service(service_id, db)
    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="Service Deleted Successfully",
        result_data=result,
    )