from contextlib import asynccontextmanager

from fastapi.responses import JSONResponse
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from db.database import connect_db, close_db
from models.base_model import StandardResponse
from routers import auth_router, user_router
from routers.customers_router import router as customers_router
from routers.menu_router import router as menu_router
from routers.enquiry_router import router as enquiry_router
from routers.session import router as session_router
from routers.services_router import router as services_router
from routers.orders_router import router as order_router
from routers.campaign_router import router as campaign_router



@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    yield
    await close_db()


app = FastAPI(
    title="Restaurant HQ FastAPI Backend",
    version="1.0.0",
    lifespan=lifespan,
    redirect_slashes=False
)

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
app.include_router(session_router, prefix="/api")
app.include_router(customers_router, prefix="/api")
app.include_router(menu_router, prefix="/api")
app.include_router(enquiry_router, prefix="/api")
app.include_router(services_router, prefix="/api")
app.include_router(order_router, prefix="/api")
app.include_router(campaign_router, prefix="/api")


@app.get("/", tags=["Health"], summary="API health check")
async def root():
    return {"status": "ok", "message": "Restaurant HQ API is running 🚀", "docs": "/docs"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
