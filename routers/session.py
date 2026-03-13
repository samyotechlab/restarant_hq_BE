from fastapi import APIRouter
from redis_client import get_session, save_session, delete_session, update_session

router = APIRouter(prefix="/session", tags=["Session"])

@router.get("/{phone}")
async def fetch_session(phone: str):
    return get_session(phone)

@router.post("/{phone}")
async def store_session(phone: str, data: dict):
    save_session(phone, data)
    return {"success": True}

@router.patch("/{phone}")
async def patch_session(phone: str, data: dict):
    updated = update_session(phone, data)
    return {"success": True, "session": updated}

@router.delete("/{phone}")
async def clear_session(phone: str):
    delete_session(phone)
    return {"success": True, "message": "Session cleared"}
