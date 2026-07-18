"""Simulation and OptimizationResult ORM models."""

from datetime import datetime
from enum import Enum
import uuid

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey, Integer,
    String, Text, Enum as SAEnum, func
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# ── Enums ─────────────────────────────────────────────────────────────────────


class SimulationStatus(str, Enum):
    QUEUED = "queued"
    MESHING = "meshing"
    RUNNING = "running"
    CONVERGED = "converged"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SolverType(str, Enum):
    CHT_MULTI_REGION = "chtMultiRegionFoam"
    BUOYANT_SIMPLE = "buoyantSimpleFoam"
    ADJOINT_SHAPE_OPT = "adjointShapeOptimizationFoam"
    CUSTOM = "custom"


# ── Simulation ────────────────────────────────────────────────────────────────


class Simulation(Base):
    __tablename__ = "simulations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ── Solver config ────────────────────────────────────────────────────────
    solver_type: Mapped[SolverType] = mapped_column(
        SAEnum(SolverType), nullable=False, default=SolverType.ADJOINT_SHAPE_OPT
    )
    status: Mapped[SimulationStatus] = mapped_column(
        SAEnum(SimulationStatus), default=SimulationStatus.QUEUED, nullable=False
    )

    # ── OpenFOAM case directory (relative to OPENFOAM_CASES_DIR) ─────────────
    case_dir: Mapped[str | None] = mapped_column(String(500))

    # ── Mesh parameters ──────────────────────────────────────────────────────
    mesh_cell_count: Mapped[int | None] = mapped_column(Integer)
    mesh_quality_score: Mapped[float | None] = mapped_column(Float)

    # ── Run parameters (JSON) ────────────────────────────────────────────────
    run_params: Mapped[dict | None] = mapped_column(
        JSONB,
        default=dict,
        doc=(
            "Stores: inlet_velocity, outlet_pressure, wall_temperature, "
            "fluid_properties, convergence_tolerance, max_iterations, etc."
        ),
    )

    # ── Convergence metrics ──────────────────────────────────────────────────
    residual_history: Mapped[list | None] = mapped_column(JSONB, default=list)
    final_residual: Mapped[float | None] = mapped_column(Float)
    iterations_completed: Mapped[int | None] = mapped_column(Integer)
    wall_time_seconds: Mapped[float | None] = mapped_column(Float)

    # ── Celery task tracking ─────────────────────────────────────────────────
    celery_task_id: Mapped[str | None] = mapped_column(String(255))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    project = relationship("Project", back_populates="simulations")
    results = relationship(
        "OptimizationResult", back_populates="simulation", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Simulation {self.id} [{self.status.value}]>"


# ── OptimizationResult ────────────────────────────────────────────────────────


class OptimizationResult(Base):
    """Stores per-iteration or final optimization output."""

    __tablename__ = "optimization_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    simulation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("simulations.id", ondelete="CASCADE"),
        nullable=False,
    )

    iteration: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # ── Result data (JSONB) ──────────────────────────────────────────────────
    metrics: Mapped[dict | None] = mapped_column(
        JSONB,
        default=dict,
        doc=(
            "Performance metrics: "
            "max_temperature, avg_temperature, pressure_drop, "
            "nusselt_number, thermal_resistance, pumping_power"
        ),
    )

    # ── File references (MinIO keys) ─────────────────────────────────────────
    vtu_file_key: Mapped[str | None] = mapped_column(String(500))   # velocity/temp field
    stl_file_key: Mapped[str | None] = mapped_column(String(500))   # optimized geometry
    porosity_field_key: Mapped[str | None] = mapped_column(String(500))

    is_final: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    simulation = relationship("Simulation", back_populates="results")

    def __repr__(self) -> str:
        tag = "FINAL" if self.is_final else f"iter={self.iteration}"
        return f"<OptResult {tag} sim={self.simulation_id}>"
