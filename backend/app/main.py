import asyncio
import logging
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import text
from starlette.middleware.trustedhost import TrustedHostMiddleware

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
    from app.services.runtime import acquire_lease
    from app.services.signals import poll_due_feeds

    with SessionLocal() as db:
        if not acquire_lease(db, "signal_poll", 840):
            db.rollback()
            return
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
    settings.assert_production()
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
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.hosts)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Persona"],
)


@app.middleware("http")
async def bind_session_user(request: Request, call_next):
    from app.security.auth import reset_request_user, session_for, set_request_user

    user_id = None
    authorization = request.headers.get("authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() == "bearer" and token.strip():
        with SessionLocal() as db:
            session = session_for(db, token.strip())
            user_id = session.user_id if session else None
    context = set_request_user(user_id)
    try:
        return await call_next(request)
    finally:
        reset_request_user(context)


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
    from app.services.golden import golden_accuracy

    db_ok = _database_ok()
    return HealthOut(
        status="ok" if db_ok else "degraded",
        service="campusflow-ai",
        database="ok" if db_ok else "error",
        ai_mode=settings.ai_mode,
        gemini_model=settings.gemini_model,
        fallback_golden_accuracy=golden_accuracy(),
        security=[
            "pii_redaction",
            "prompt_injection_guard",
            "rbac",
            "rate_limit",
            "schema_validation",
            "security_headers",
            "trusted_host",
            "rss_8h_schedule",
            "public_feed_ssrf_guard",
            "production_boot_guard",
            "faculty_cosign",
            "pinned_model",
        ],
    )


app.include_router(auth_router)
app.include_router(router)
app.include_router(signals_router)
