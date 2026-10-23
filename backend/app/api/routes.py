"""
SlothDesk API routes.

All endpoints use consistent Pydantic response models, appropriate HTTP
status codes, and centralized exception handling.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.config import get_settings
from app.schemas import (
    ApplyRequest,
    ApplyResponse,
    DuplicatesResponse,
    ErrorResponse,
    HealthResponse,
    HistoryResponse,
    OllamaStatusResponse,
    OperationStatus,
    PlanResponse,
    ScanResponse,
    StatsResponse,
)
from app.services import scanner, ai, planner, organizer, history
from app.services.ollama import OllamaClient, OllamaError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

# ── Helpers ─────────────────────────────────────────────────────


def _get_ollama_client() -> OllamaClient:
    """Build an Ollama client from current settings."""
    settings = get_settings()
    return OllamaClient(
        base_url=settings.ollama_url,
        model=settings.ollama_model,
        timeout_seconds=settings.ollama_timeout_seconds,
    )


# ── GET /api/health ─────────────────────────────────────────────


@router.get(
    "/health",
    response_model=HealthResponse,
    responses={500: {"model": ErrorResponse}},
)
async def health_check() -> HealthResponse:
    """Return backend health and basic configuration info."""
    settings = get_settings()
    return HealthResponse(
        status="ok",
        model=settings.ollama_model,
        root_directory=settings.slothdesk_root,
    )


# ── GET /api/ollama/status ──────────────────────────────────────


@router.get(
    "/ollama/status",
    response_model=OllamaStatusResponse,
    responses={503: {"model": ErrorResponse}},
)
async def ollama_status() -> OllamaStatusResponse:
    """Check Ollama availability and model status without triggering inference."""
    client = _get_ollama_client()
    try:
        available = await client.is_available()
        if not available:
            return OllamaStatusResponse(
                available=False,
                model=client.model,
                model_loaded=False,
                error="Ollama is not running. Start it with 'ollama serve'.",
            )

        model_loaded = await client.is_model_available()
        error = None
        if not model_loaded:
            error = f"Model '{client.model}' not found. Run 'ollama pull {client.model}'."

        return OllamaStatusResponse(
            available=True,
            model=client.model,
            model_loaded=model_loaded,
            error=error,
        )
    finally:
        await client.close()


# ── GET /api/scan ───────────────────────────────────────────────


@router.get(
    "/scan",
    response_model=ScanResponse,
    responses={500: {"model": ErrorResponse}},
)
async def scan_files() -> ScanResponse:
    """Scan the configured root directory and return file inventory."""
    settings = get_settings()
    settings.validate_root_exists()

    try:
        files = scanner.scan_directory(
            root=settings.slothdesk_root,
            max_files=settings.max_scan_files,
            max_file_size_bytes=settings.max_file_size_bytes,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Scan failed: {exc}")

    return ScanResponse(
        files=files,
        total=len(files),
        root_directory=settings.slothdesk_root,
    )


# ── POST /api/plan ──────────────────────────────────────────────


@router.post(
    "/plan",
    response_model=PlanResponse,
    responses={
        400: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def generate_plan() -> PlanResponse:
    """
    Scan, classify with the local AI, validate, and return proposed actions.

    This endpoint NEVER modifies files.
    """
    settings = get_settings()
    settings.validate_root_exists()

    # Step 1: Scan
    try:
        files = scanner.scan_directory(
            root=settings.slothdesk_root,
            max_files=settings.max_scan_files,
        )
    except (FileNotFoundError, OSError) as exc:
        raise HTTPException(status_code=500, detail=f"Scan failed: {exc}")

    if not files:
        return PlanResponse(actions=[], total=0)

    # Step 2: AI classification
    client = _get_ollama_client()
    try:
        raw_actions = await ai.classify_files(client, files)
    except OllamaError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))
    finally:
        await client.close()

    if not raw_actions:
        return PlanResponse(actions=[], total=0)

    # Step 3: Server-side validation (AI is never trusted)
    valid_actions, rejected = planner.validate_plan(
        actions=raw_actions,
        inventory=files,
        root=settings.slothdesk_root,
        max_actions=settings.max_plan_actions,
    )

    if rejected:
        logger.info(
            "Plan validation rejected %d actions: %s",
            len(rejected),
            [r["reason"] for r in rejected[:5]],
        )

    return PlanResponse(actions=valid_actions, total=len(valid_actions))


# ── POST /api/apply ─────────────────────────────────────────────


@router.post(
    "/apply",
    response_model=ApplyResponse,
    responses={
        400: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
)
async def apply_plan(request: ApplyRequest) -> ApplyResponse:
    """
    Execute approved file moves after full revalidation.

    Requires explicit confirmation (confirmed=true).
    """
    settings = get_settings()
    settings.validate_root_exists()

    if not request.confirmed:
        raise HTTPException(status_code=400, detail="Explicit confirmation required. Set confirmed=true.")

    if not request.actions:
        raise HTTPException(status_code=400, detail="No actions provided.")

    if len(request.actions) > settings.max_plan_actions:
        raise HTTPException(
            status_code=400,
            detail=f"Too many actions. Maximum is {settings.max_plan_actions}.",
        )

    try:
        operation_id, results = organizer.validate_and_execute(
            actions=request.actions,
            confirmed=request.confirmed,
            root=settings.slothdesk_root,
        )
    except organizer.OrganizeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # Build backward-compatible response
    moved = [r.source for r in results if r.status == OperationStatus.SUCCESS]
    skipped = [r.source for r in results if r.status in (OperationStatus.SKIPPED, OperationStatus.FAILED)]

    # Persist to SQLite
    categories = {a.source: a.category for a in request.actions}
    try:
        history.record_operations(
            operation_id=operation_id,
            results=results,
            categories=categories,
        )
    except Exception as exc:
        logger.error("Failed to persist history: %s", exc)
        # Don't fail the response — the moves already happened

    return ApplyResponse(
        moved=moved,
        skipped=skipped,
        results=results,
        operation_id=operation_id,
    )


# ── GET /api/history ────────────────────────────────────────────


@router.get(
    "/history",
    response_model=HistoryResponse,
    responses={500: {"model": ErrorResponse}},
)
async def get_history(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Records per page"),
) -> HistoryResponse:
    """Return paginated operation history from SQLite."""
    try:
        records, total = history.get_history(page=page, page_size=page_size)
    except Exception as exc:
        logger.error("History retrieval failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to retrieve history.")

    return HistoryResponse(
        records=records,
        total=total,
        page=page,
        page_size=page_size,
    )


# ── GET /api/stats ──────────────────────────────────────────────


@router.get(
    "/stats",
    response_model=StatsResponse,
    responses={500: {"model": ErrorResponse}},
)
async def get_stats() -> StatsResponse:
    """Return metrics computed from real scan results and operation history."""
    settings = get_settings()

    # Current file count from a fresh scan (if root exists)
    files_scanned = 0
    try:
        if settings.slothdesk_root and __import__("os").path.isdir(settings.slothdesk_root):
            files = scanner.scan_directory(
                root=settings.slothdesk_root,
                max_files=settings.max_scan_files,
            )
            files_scanned = len(files)
    except Exception:
        pass

    # Historical stats from SQLite
    try:
        stats = history.get_stats()
    except Exception:
        stats = {}

    return StatsResponse(
        files_scanned=files_scanned,
        total_operations=stats.get("total_operations", 0),
        successful_moves=stats.get("successful_moves", 0),
        failed_moves=stats.get("failed_moves", 0),
        categories=stats.get("categories", {}),
    )


# ── GET /api/duplicates ────────────────────────────────────────


@router.get(
    "/duplicates",
    response_model=DuplicatesResponse,
    responses={500: {"model": ErrorResponse}},
)
async def find_duplicates() -> DuplicatesResponse:
    """Identify duplicate files by SHA-256 hash. Never deletes anything."""
    settings = get_settings()
    settings.validate_root_exists()

    try:
        groups = scanner.find_duplicates(
            root=settings.slothdesk_root,
            max_files=settings.max_scan_files,
            max_file_size_bytes=settings.max_file_size_bytes,
        )
    except (FileNotFoundError, OSError) as exc:
        raise HTTPException(status_code=500, detail=f"Duplicate detection failed: {exc}")

    total_duplicate_files = sum(len(g.paths) for g in groups)

    return DuplicatesResponse(
        groups=groups,
        total_duplicate_files=total_duplicate_files,
    )
