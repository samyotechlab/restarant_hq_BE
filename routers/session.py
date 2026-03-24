from fastapi import APIRouter
from redis_client import get_session, save_session, delete_session, update_session

router = APIRouter(prefix="/session", tags=["Session"])

@router.get("/{phone}", include_in_schema=False)
async def fetch_session(phone: str):
    return get_session(phone)

@router.post("/{phone}", include_in_schema=False)
async def store_session(phone: str, data: dict):
    save_session(phone, data)
    return {"success": True}

@router.patch("/{phone}", include_in_schema=False)
async def patch_session(phone: str, data: dict):
    updated = update_session(phone, data)
    return {"success": True, "session": updated}

@router.delete("/{phone}", include_in_schema=False)
async def clear_session(phone: str):
    delete_session(phone)
    return {"success": True, "message": "Session cleared"}
