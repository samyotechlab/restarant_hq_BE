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

r_feedback = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    password=settings.REDIS_PASSWORD,
    decode_responses=True,
    db=1,
    ssl=False
)

FEEDBACK_EXPIRY = 172800


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


# ── Store feedback queue entry ────────────────────────────────
def store_feedback_queue(order_id: str, phone: str, session_id: str, customer_name: str, send_date: str) -> bool:
    data = {
        "order_id": order_id,
        "phone": phone,
        "session_id": session_id,
        "customer_name": customer_name,
        "send_date": send_date,
        "sent": False,
        "created_at": datetime.utcnow().isoformat()
    }
    r_feedback.setex(
        f"feedback:{order_id}",
        FEEDBACK_EXPIRY,
        json.dumps(data)
    )
    return True


# ── Get all pending feedback for a date ───────────────────────
async def get_pending_feedback(send_date: str) -> list:
    keys: list[str] = []
    cursor: int = 0

    while True:
        result = await r_feedback.scan(cursor=cursor, match="feedback:*", count=100)
        cursor = int(result[0])
        batch: list[str] = list(result[1])
        keys.extend(batch)
        if cursor == 0:
            break

    pending = []
    for key in keys:
        raw: str | None = r_feedback.get(key)  # type: ignore
        if raw:
            entry: dict = json.loads(raw)
            if entry.get("send_date") == send_date and not entry.get("sent"):
                pending.append(entry)
    return pending



# ── Mark feedback as sent ─────────────────────────────────────
def mark_feedback_sent(order_id: str) -> bool:
    key = f"feedback:{order_id}"
    raw: str | None = r_feedback.get(key) # type: ignore
    if raw:
        entry: dict = json.loads(raw)
        entry["sent"] = True
        r_feedback.setex(key, 3600, json.dumps(entry))
    return True


# ── Delete feedback entry ─────────────────────────────────────
def delete_feedback(order_id: str) -> bool:
    r_feedback.delete(f"feedback:{order_id}")
    return True