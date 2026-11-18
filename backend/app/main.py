import asyncio
import logging
from contextlib import asynccontextmanager
from contextlib import suppress

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import text

from app.config import get_settings
from app.database import SessionLocal, init_db
from app.limiter import limiter
from app.routers.api import router
from app.routers.auth import router as auth_router
from app.routers.signals import router as signals_router
from app.schemas import HealthOut

settings = get_settings()
logger = logging.getLogger("campusflow")


def _poll_once() -> None:
    from app.services.signals import poll_due_feeds

    with SessionLocal() as db:
        poll_due_feeds(db)
        db.commit()


async def _signal_loop() -> None:
    while True:
        await asyncio.sleep(900)
        try:
            await asyncio.to_thread(_poll_once)
        except Exception:
            logger.exception("Scheduled feed poll failed")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    task = asyncio.create_task(_signal_loop())
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


app = FastAPI(
    title="CampusFlow AI",
    summary="Agile campus operating system",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None,
    openapi_url=None if settings.is_production else "/openapi.json",
)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Persona"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(_request: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"detail": "Rate limit reached. Wait a minute and try the AI action again."})


def _database_ok() -> bool:
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


@app.get("/health", response_model=HealthOut)
def health() -> HealthOut:
    return HealthOut(
        status="ok" if _database_ok() else "degraded",
        service="campusflow-ai",
        database="ok" if _database_ok() else "error",
        ai_mode=settings.ai_mode,
        security=[
            "pii_redaction",
            "prompt_injection_guard",
            "rbac",
            "rate_limit",
            "schema_validation",
            "security_headers",
            "rss_8h_schedule",
            "public_feed_ssrf_guard",
        ],
    )


app.include_router(auth_router)
app.include_router(router)
app.include_router(signals_router)
