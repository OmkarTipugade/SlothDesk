"""
SlothDesk Pydantic v2 schemas for API requests and responses.

These schemas define the contract between the backend and the React frontend.
They are also used internally for AI response validation and plan verification.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Enums ───────────────────────────────────────────────────────


class FileCategory(str, Enum):
    """Allowed organization categories. The AI model must choose from these."""
    DOCUMENTS = "Documents"
    IMAGES = "Images"
    AUDIO = "Audio"
    VIDEO = "Video"
    CODE = "Code"
    DATA = "Data"
    INVOICES = "Invoices"
    RESUMES = "Resumes"
    NOTES = "Notes"
    OTHER = "Other"


class OperationStatus(str, Enum):
    """Status for each individual file move operation."""
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    ROLLED_BACK = "rolled_back"


# ── File Inventory ──────────────────────────────────────────────


class FileRecord(BaseModel):
    """Metadata for a single scanned file. No file contents are included."""
    name: str
    relative_path: str
    extension: str
    size_bytes: int
    last_modified: Optional[float] = None
    file_type: Optional[str] = None


class ScanResponse(BaseModel):
    """Response from GET /api/scan."""
    files: List[FileRecord]
    total: int = 0
    root_directory: str = ""


# ── AI / Plan ───────────────────────────────────────────────────


class PlanAction(BaseModel):
    """A single proposed file move action from the AI or validated plan."""
    source: str = Field(..., description="Relative path of the source file")
    destination: str = Field(..., description="Relative path of the destination")
    category: str = Field(..., description="Organization category")
    reason: str = Field("", description="Brief reason for this categorization")


class PlanResponse(BaseModel):
    """Response from POST /api/plan."""
    actions: List[PlanAction]
    total: int = 0


class AIPlanOutput(BaseModel):
    """
    Schema the AI model must produce.
    Used for structured output validation of Ollama responses.
    """
    actions: List[PlanAction]


# ── Apply / Organize ───────────────────────────────────────────


class ApplyRequest(BaseModel):
    """Request body for POST /api/apply."""
    actions: List[PlanAction]
    confirmed: bool = False


class ActionResult(BaseModel):
    """Result for a single file move operation."""
    source: str
    destination: str
    status: OperationStatus
    error: Optional[str] = None


class ApplyResponse(BaseModel):
    """
    Response from POST /api/apply.

    The `moved` and `skipped` fields maintain backward-compatibility with
    the frontend's existing ApplyResult type. The `results` field provides
    more detailed per-action status.
    """
    moved: List[str] = Field(default_factory=list)
    skipped: List[str] = Field(default_factory=list)
    results: List[ActionResult] = Field(default_factory=list)
    operation_id: Optional[str] = None


# ── Health ──────────────────────────────────────────────────────


class HealthResponse(BaseModel):
    """Response from GET /api/health."""
    status: str = "ok"
    model: Optional[str] = None
    root_directory: Optional[str] = None


class OllamaStatusResponse(BaseModel):
    """Response from GET /api/ollama/status."""
    available: bool
    model: str
    model_loaded: bool
    error: Optional[str] = None


# ── History ─────────────────────────────────────────────────────


class HistoryRecord(BaseModel):
    """A persisted operation record from SQLite."""
    id: int
    operation_id: str
    timestamp: str
    source: str
    destination: str
    category: str
    status: str
    error: Optional[str] = None
    source_fingerprint: Optional[str] = None


class HistoryResponse(BaseModel):
    """Response from GET /api/history."""
    records: List[HistoryRecord]
    total: int
    page: int
    page_size: int


# ── Stats ───────────────────────────────────────────────────────


class StatsResponse(BaseModel):
    """Response from GET /api/stats — computed from real data only."""
    files_scanned: int = 0
    total_operations: int = 0
    successful_moves: int = 0
    failed_moves: int = 0
    categories: Dict[str, int] = Field(default_factory=dict)


# ── Duplicates ──────────────────────────────────────────────────


class DuplicateGroup(BaseModel):
    """A group of files that share the same SHA-256 hash."""
    hash: str
    size_bytes: int
    paths: List[str]


class DuplicatesResponse(BaseModel):
    """Response from GET /api/duplicates."""
    groups: List[DuplicateGroup]
    total_duplicate_files: int = 0


# ── Error ───────────────────────────────────────────────────────


class ErrorResponse(BaseModel):
    """Standard error response body."""
    detail: str
    code: Optional[str] = None
