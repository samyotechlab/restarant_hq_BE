from contextlib import asynccontextmanager
from datetime import datetime, timezone
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from db.database import connect_db, close_db
from models.base_model import StandardResponse
from models.offers_model import OfferStatus
from routers import auth_router, user_router
from routers.customers_router import router as customers_router
from routers.menu_router import router as menu_router
from routers.enquiry_router import router as enquiry_router
from routers.session import router as session_router
from routers.services_router import router as services_router
from routers.orders_router import router as order_router
from routers.feedback_router import router as feedback_router
from routers.offer_router import router as offer_router
from routers.help_ticket_router import router as help_ticket_router
from routers.feedback import router as feedback_queue_router
from routers.upsell_item_router import router as upsell_item_router
from routers.campaign_router import router as campaign_router

async def check_offer_status_updates():
    """Background task to sync campaign statuses in MongoDB."""
    from db.database import get_db
    db = get_db()
    if db is None:
        print("⏳ Scheduler: Waiting for DB connection...")
        return

    now = datetime.now(timezone.utc)
    campaigns_col = db["campaigns"]

    start_result = await campaigns_col.update_many(
        {
            "status": OfferStatus.SCHEDULED.value,
            "start_date": {"$lte": now}
        },
        {"$set": {"status": OfferStatus.ACTIVE.value, "updated_at": now}}
    )
    
    end_result = await campaigns_col.update_many(
        {
            "status": OfferStatus.ACTIVE.value,
            "end_date": {"$lte": now}
        },
        {"$set": {"status": OfferStatus.COMPLETED.value, "updated_at": now}}
    )

    if start_result.modified_count > 0:
        print(f"🚀 Activated {start_result.modified_count} campaigns.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_offer_status_updates, 'interval', minutes=10)
    scheduler.start()
    app.state.scheduler = scheduler
    print("✅ Database connected and Scheduler started")
    
    yield
    scheduler.shutdown()
    await close_db()
    print("🛑 Scheduler stopped and Database connection closed")

app = FastAPI(
    title="Restaurant HQ FastAPI Backend",
    version="1.0.0",
    lifespan=lifespan,
    redirect_slashes=False
)
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:8080",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:8080",
    "https://mygangour.samyotech.in",
    "https://mygangour.com"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=StandardResponse(
            status_code=exc.status_code,
            message=exc.detail,
            result_data=None,
        ).model_dump(),
    )


app.include_router(auth_router, prefix="/api")
app.include_router(user_router, prefix="/api")
app.include_router(campaign_router, prefix="/api")
app.include_router(session_router, prefix="/api")
app.include_router(feedback_queue_router, prefix="/api")
app.include_router(customers_router, prefix="/api")
app.include_router(menu_router, prefix="/api")
app.include_router(enquiry_router, prefix="/api")
app.include_router(services_router, prefix="/api")
app.include_router(order_router, prefix="/api")
app.include_router(feedback_router, prefix="/api")
app.include_router(offer_router, prefix="/api")
app.include_router(help_ticket_router, prefix="/api")
app.include_router(upsell_item_router, prefix="/api")


@app.get("/", tags=["Health"], summary="API health check")
async def root():
    return {"status": "ok", "message": "Restaurant HQ API is running 🚀", "docs": "/docs"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
