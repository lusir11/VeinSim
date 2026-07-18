"""Project ORM model — represents a cold-plate / heat-exchanger design project."""

from datetime import datetime
from enum import Enum
import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, Enum as SAEnum, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ProjectStatus(str, Enum):
    DRAFT = "draft"
    DESIGNING = "designing"
    OPTIMIZING = "optimizing"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ManufacturingProcess(str, Enum):
    STAMPING = "stamping"
    CNC = "cnc"
    CHEMICAL_ETCHING = "chemical_etching"
    ADDITIVE_3D_PRINT = "3d_print"


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ProjectStatus] = mapped_column(
        SAEnum(ProjectStatus), default=ProjectStatus.DRAFT, nullable=False
    )

    # ── Geometry metadata ────────────────────────────────────────────────────
    geometry_file_key: Mapped[str | None] = mapped_column(String(500))  # MinIO object key
    geometry_format: Mapped[str | None] = mapped_column(String(20))     # stl, step, iges

    # ── Design constraints (JSON) ────────────────────────────────────────────
    constraints: Mapped[dict | None] = mapped_column(
        JSONB,
        default=dict,
        doc=(
            "JSON blob storing: "
            "max_temperature, max_pressure_drop, flow_rate, "
            "heat_source_positions, manufacturing_process, etc."
        ),
    )

    # ── Manufacturing process constraint ─────────────────────────────────────
    manufacturing_process: Mapped[ManufacturingProcess | None] = mapped_column(
        SAEnum(ManufacturingProcess), nullable=True
    )

    # ── Ownership ────────────────────────────────────────────────────────────
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    owner = relationship("User", back_populates="projects")
    simulations = relationship("Simulation", back_populates="project", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Project {self.name!r} [{self.status.value}]>"
