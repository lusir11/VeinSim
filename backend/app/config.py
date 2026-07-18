"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global application settings."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ── Database ─────────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://tofeex:tofeex_dev_2026@localhost:5432/tofeex_db"

    # ── Redis ────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Celery ───────────────────────────────────────────────────────────────
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # ── MinIO ────────────────────────────────────────────────────────────────
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ROOT_USER: str = "minioadmin"
    MINIO_ROOT_PASSWORD: str = "minioadmin_secret"
    MINIO_BUCKET: str = "tofeex-models"

    # ── Auth / JWT ───────────────────────────────────────────────────────────
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # ── OpenFOAM Solver ─────────────────────────────────────────────────────
    OPENFOAM_CASES_DIR: str = "/opt/openfoam/cases"
    SOLVER_TIMEOUT_SECONDS: int = 7200
    SOLVER_MAX_PARALLEL: int = 4
    SOLVER_MOCK: bool = False  # True = use mock solver (no OpenFOAM needed)

    # ── App meta ─────────────────────────────────────────────────────────────
    APP_NAME: str = "VeinSim API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True


settings = Settings()
