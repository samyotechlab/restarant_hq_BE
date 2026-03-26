from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime, timedelta
from redis_client import (
    store_feedback_queue,
    get_pending_feedback,
    mark_feedback_sent,
    delete_feedback
)

router = APIRouter(prefix="/feedback-queue", tags=["Feedback Queue"])


# ── Request Models ────────────────────────────────────────────
class FeedbackStoreRequest(BaseModel):
    order_id: str
    phone: str
    session_id: str
    customer_name: str
    days_later: int = 1  # default next day


class MarkSentRequest(BaseModel):
    order_id: str


# ── Store feedback in queue ───────────────────────────────────
@router.post("/store")
def store_feedback(payload: FeedbackStoreRequest):
    try:
        send_date = (datetime.utcnow() + timedelta(days=payload.days_later)).strftime("%Y-%m-%d")
        store_feedback_queue(
            order_id=payload.order_id,
            phone=payload.phone,
            session_id=payload.session_id,
            customer_name=payload.customer_name,
            send_date=send_date
        )
        return {
            "status": "ok",
            "message": "Feedback queued",
            "send_date": send_date
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Get pending feedbacks for today ───────────────────────────
@router.get("/pending")
def pending_feedback(date: str = None): # type: ignore
    try:
        target_date = date or datetime.utcnow().strftime("%Y-%m-%d")
        data = get_pending_feedback(target_date)
        return {
            "status": "ok",
            "date": target_date,
            "count": len(data), # type: ignore
            "feedbacks": data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Mark feedback as sent ─────────────────────────────────────
@router.post("/mark-sent")
def mark_sent(payload: MarkSentRequest):
    try:
        mark_feedback_sent(payload.order_id)
        return {
            "status": "ok",
            "message": f"Feedback {payload.order_id} marked as sent"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Delete feedback entry (optional) ─────────────────────────
@router.delete("/delete/{order_id}")
def delete_feedback_entry(order_id: str):
    try:
        delete_feedback(order_id)
        return {
            "status": "ok",
            "message": f"Feedback {order_id} deleted"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
