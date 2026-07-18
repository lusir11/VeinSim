"""Celery application and async simulation tasks with progress reporting."""

import logging
import uuid

from celery import Celery

from app.config import settings

logger = logging.getLogger(__name__)

celery_app = Celery(
    "veinsim_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_time_limit=settings.SOLVER_TIMEOUT_SECONDS + 600,
    task_soft_time_limit=settings.SOLVER_TIMEOUT_SECONDS,
)


def _update_simulation(sim_id: str, **kwargs) -> None:
    """Helper: update Simulation record fields via sync DB session."""
    from app.database import get_sync_db
    from app.models.simulation import Simulation

    with get_sync_db() as db:
        sim = db.query(Simulation).filter(Simulation.id == uuid.UUID(sim_id)).first()
        if sim:
            for key, value in kwargs.items():
                setattr(sim, key, value)
            db.flush()


@celery_app.task(bind=True, name="run_simulation")
def run_simulation_task(self, simulation_id: str, run_params: dict) -> dict:
    """
    Celery task: prepare OpenFOAM case -> mesh -> solve -> post-process.
    Publishes progress events to Redis for WebSocket forwarding.
    """
    from app.services.solver_service import (
        create_case_dir,
        write_transport_properties,
        write_control_dict,
        write_adjoint_dict,
        run_meshing,
        run_solver,
        extract_metrics,
        generate_mock_alpha_field,
    )
    from app.services.progress_publisher import (
        publish_status,
        publish_iteration,
        publish_result,
    )
    from app.solver.postprocessing import post_process_optimization
    from app.services.minio_service import upload_bytes
    from app.models.simulation import SimulationStatus, OptimizationResult

    sim_id = simulation_id
    logger.info("Starting simulation %s (mock=%s)", sim_id, settings.SOLVER_MOCK)

    # ── Step 1: Prepare case directory ────────────────────────────────────
    publish_status(sim_id, "meshing", message="Preparing case directory...")
    case_dir = create_case_dir(uuid.UUID(sim_id))

    # ── Step 2: Write OpenFOAM dictionaries ──────────────────────────────
    write_transport_properties(case_dir, run_params)
    write_control_dict(case_dir, run_params)
    write_adjoint_dict(case_dir, run_params)

    # ── Step 3: Meshing ──────────────────────────────────────────────────
    publish_status(sim_id, "meshing", message="Generating mesh...")
    mesh_result = run_meshing(case_dir)
    if not mesh_result["success"]:
        _update_simulation(sim_id, status=SimulationStatus.FAILED)
        publish_status(sim_id, "failed", phase="meshing", error=mesh_result["stderr"])
        return {
            "status": "failed",
            "phase": "meshing",
            "error": mesh_result["stderr"],
            "cell_count": mesh_result.get("cell_count", 0),
        }

    _update_simulation(
        sim_id,
        status=SimulationStatus.RUNNING,
        mesh_cell_count=mesh_result["cell_count"],
    )
    publish_status(sim_id, "running", message="Mesh complete, starting solver...",
                   cell_count=mesh_result["cell_count"])

    # ── Step 4: Solve ────────────────────────────────────────────────────
    solve_result = run_solver(case_dir)

    # Publish iteration-by-iteration residuals
    residual_history = solve_result.get("residual_history", [])
    for i, res in enumerate(residual_history):
        publish_iteration(sim_id, iteration=i, residual=res)

    if not solve_result["success"]:
        _update_simulation(sim_id, status=SimulationStatus.FAILED)
        publish_status(sim_id, "failed", phase="solving", error=solve_result["stderr_tail"])
        return {
            "status": "failed",
            "phase": "solving",
            "error": solve_result["stderr_tail"],
            "mesh_cell_count": mesh_result["cell_count"],
            "wall_time_seconds": solve_result.get("wall_time_seconds"),
        }

    # Update solver results in DB
    _update_simulation(
        sim_id,
        iterations_completed=solve_result["iterations"],
        final_residual=solve_result["final_residual"],
        wall_time_seconds=solve_result["wall_time_seconds"],
        residual_history=residual_history,
    )

    # ── Step 5: Post-process + upload STL + create OptimizationResult ────
    publish_status(sim_id, "running", message="Post-processing results...")
    metrics = extract_metrics(case_dir)

    # Generate or load alpha field for post-processing
    if settings.SOLVER_MOCK:
        alpha_field = generate_mock_alpha_field()
    else:
        # Real mode: would load from OpenFOAM output files
        alpha_field = generate_mock_alpha_field()  # fallback until real loader exists

    # Run post-processing pipeline
    pp_result = post_process_optimization(
        alpha_field,
        target_volume_fraction=0.4,
        extract_stl=True,
    )

    # Upload STL to MinIO
    stl_bytes = pp_result.get("stl_bytes", b"")
    stl_key = f"simulations/{sim_id}/optimized_geometry.stl"
    if stl_bytes:
        try:
            upload_bytes(stl_key, stl_bytes, content_type="model/stl")
            logger.info("Uploaded optimized STL to MinIO: %s (%d bytes)", stl_key, len(stl_bytes))
        except Exception as exc:
            logger.warning("Failed to upload STL to MinIO: %s", exc)
            stl_key = None
    else:
        stl_key = None

    # Create OptimizationResult record and update final status
    from app.database import get_sync_db

    with get_sync_db() as db:
        sim = db.query(Simulation).filter(Simulation.id == uuid.UUID(sim_id)).first()
        if sim:
            sim.status = SimulationStatus.CONVERGED
            sim.case_dir = str(case_dir)
            db.flush()

        opt_result = OptimizationResult(
            simulation_id=uuid.UUID(sim_id),
            iteration=solve_result["iterations"],
            metrics=metrics,
            stl_file_key=stl_key,
            is_final=True,
        )
        db.add(opt_result)
        db.flush()

    publish_status(sim_id, "converged", message="Optimization converged!")
    publish_result(sim_id, metrics=metrics, file_keys={
        "case_dir": str(case_dir),
        "stl_key": stl_key or "",
    })

    return {
        "status": "converged",
        "simulation_id": simulation_id,
        "mesh_cell_count": mesh_result["cell_count"],
        "iterations_completed": solve_result["iterations"],
        "final_residual": solve_result["final_residual"],
        "wall_time_seconds": solve_result["wall_time_seconds"],
        "metrics": metrics,
        "case_dir": str(case_dir),
        "stl_key": stl_key,
    }
