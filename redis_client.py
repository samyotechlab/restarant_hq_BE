import redis
import json
import os
from datetime import datetime
from dotenv import load_dotenv

from config.settings import settings

load_dotenv()

# ── Connect ───────────────────────────────────────────────────
r = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    password=settings.REDIS_PASSWORD,
    decode_responses=True,
    ssl=False
)

SESSION_EXPIRY = 86400

# ── Default empty session ─────────────────────────────────────
def default_session(phone: str) -> dict:
    return {
        "phone": phone,
        "current_module": None,
        "conversation_stage": None,
        "cart_items": [],
        "cart_total": 0,
        "last_intent": None,
        "last_active": datetime.utcnow().isoformat()
    }

# ── Get session ───────────────────────────────────────────────
def get_session(phone: str) -> dict:
    data = r.get(f"session:{phone}")
    if data:
        return json.loads(data)  # type: ignore
    return default_session(phone)

# ── Save full session ─────────────────────────────────────────
def save_session(phone: str, session: dict) -> bool:
    session["last_active"] = datetime.utcnow().isoformat()
    r.setex(
        f"session:{phone}",
        SESSION_EXPIRY,
        json.dumps(session)
    )
    return True

# ── Update specific fields only ───────────────────────────────
def update_session(phone: str, updates: dict) -> dict:
    session = get_session(phone)
    session.update(updates)
    save_session(phone, session)
    return session

# ── Delete session ────────────────────────────────────────────
def delete_session(phone: str) -> bool:
    r.delete(f"session:{phone}")
    return True
