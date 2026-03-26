from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime, timedelta
from redis_client import (
    store_feedback_queue,
    get_pending_feedback,
    mark_feedback_sent,
    delete_feedback,
    get_feedback
)

router = APIRouter(prefix="/feedback-queue", tags=["Feedback Queue"])


# ── Request Models ────────────────────────────────────────────
class FeedbackStoreRequest(BaseModel):
    order_id: str
    phone: str
    session_id: str
    customer_name: str
    days_later: int = 1


class MarkSentRequest(BaseModel):
    order_id: str


# ── Store feedback in queue ───────────────────────────────────
@router.post("/store")
def store_feedback(payload: FeedbackStoreRequest):
    try:
        send_date = (
            datetime.utcnow() + timedelta(days=payload.days_later)
        ).strftime("%Y-%m-%d")

        success = store_feedback_queue(
            order_id=payload.order_id,
            phone=payload.phone,
            session_id=payload.session_id,
            customer_name=payload.customer_name,
            send_date=send_date
        )

        if not success:
            raise HTTPException(status_code=400, detail="Failed to store feedback. Check required fields.")

        return {
            "status": "ok",
            "message": "Feedback queued successfully",
            "order_id": payload.order_id,
            "send_date": send_date
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Get pending feedbacks for today or given date ─────────────
@router.get("/pending")
def pending_feedback(date: str = None): # pyright: ignore[reportArgumentType]
    try:
        target_date = date or datetime.utcnow().strftime("%Y-%m-%d")
        data = get_pending_feedback(target_date)
        return {
            "status": "ok",
            "date": target_date,
            "count": len(data),
            "feedbacks": data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Mark feedback as sent ─────────────────────────────────────
@router.post("/mark-sent")
def mark_sent(payload: MarkSentRequest):
    try:
        success = mark_feedback_sent(payload.order_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Feedback {payload.order_id} not found or already sent")
        return {
            "status": "ok",
            "message": f"Feedback {payload.order_id} marked as sent"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Get specific feedback entry ───────────────────────────────
@router.get("/get/{order_id}")
def get_feedback_entry(order_id: str):
    try:
        entry = get_feedback(order_id)
        if not entry:
            raise HTTPException(status_code=404, detail=f"Feedback {order_id} not found")
        return {
            "status": "ok",
            "feedback": entry
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Delete feedback entry ─────────────────────────────────────
@router.delete("/delete/{order_id}")
def delete_feedback_entry(order_id: str):
    try:
        success = delete_feedback(order_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Feedback {order_id} not found")
        return {
            "status": "ok",
            "message": f"Feedback {order_id} deleted"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
