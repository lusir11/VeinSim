"""VeinSim — FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.api.v1.router import api_router

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ── Lifespan ──────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown hooks."""
    logger.info("Initializing database tables …")
    await init_db()
    logger.info("Database ready.")

    # Pre-create MinIO bucket (non-blocking best-effort)
    try:
        from app.services.minio_service import ensure_bucket
        ensure_bucket()
    except Exception as exc:
        logger.warning("MinIO bucket init skipped: %s", exc)

    # Start Redis pub/sub -> WebSocket progress bridge
    try:
        from app.services.progress_bridge import start_progress_bridge
        await start_progress_bridge()
        logger.info("Progress bridge started.")
    except Exception as exc:
        logger.warning("Progress bridge skipped: %s", exc)
    
    yield
    
    # Shutdown progress bridge
    try:
        from app.services.progress_bridge import stop_progress_bridge
        await stop_progress_bridge()
    except Exception:
        pass
    logger.info("Shutting down \u2026")


# ── App instance ──────────────────────────────────────────────────────────────


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Cloud-native generative design platform for thermal-fluid components. "
        "Physics-driven topology optimization for cold plates, heat exchangers, and manifolds."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register routers ─────────────────────────────────────────────────────────

app.include_router(api_router)


# ── Health check ──────────────────────────────────────────────────────────────


@app.get("/health", tags=["meta"])
async def health_check():
    return {"status": "ok", "version": settings.APP_VERSION}
