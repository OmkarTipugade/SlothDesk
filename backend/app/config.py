"""
SlothDesk configuration — validated settings loaded from environment variables.

All filesystem paths are resolved to absolute paths at startup.
The application refuses to start if the configured root directory does not exist.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings


def _default_root() -> str:
    """Return a safe default working directory inside the user's home."""
    return os.path.join(Path.home(), "SlothDesk_Demo")


def _default_db_path() -> str:
    """Store the database alongside the backend code, outside the scanned directory."""
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), ".slothdesk_data", "history.db")


class Settings(BaseSettings):
    """Application settings with sensible local defaults."""

    # ── Filesystem ──────────────────────────────────────────────
    slothdesk_root: str = _default_root()
    database_path: str = _default_db_path()

    # ── Ollama ──────────────────────────────────────────────────
    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen3:4b"
    ollama_timeout_seconds: int = 180

    # ── Limits ──────────────────────────────────────────────────
    max_scan_files: int = 500
    max_file_size_mb: int = 50
    max_plan_actions: int = 100

    # ── CORS ────────────────────────────────────────────────────
    cors_origins: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    # ── Server ──────────────────────────────────────────────────
    host: str = "127.0.0.1"
    port: int = 8000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        # Allow environment variables like SLOTHDESK_ROOT, OLLAMA_URL, etc.
        case_sensitive = False

    # ── Validators ──────────────────────────────────────────────

    @field_validator("slothdesk_root")
    @classmethod
    def _resolve_root(cls, v: str) -> str:
        resolved = os.path.realpath(os.path.expanduser(v))
        return resolved

    @field_validator("database_path")
    @classmethod
    def _resolve_db(cls, v: str) -> str:
        return os.path.realpath(os.path.expanduser(v))

    def validate_root_exists(self) -> None:
        """Raise if the configured root is not a real directory."""
        if not os.path.isdir(self.slothdesk_root):
            raise RuntimeError(
                f"SLOTHDESK_ROOT does not exist or is not a directory: {self.slothdesk_root!r}. "
                f"Create it first or set SLOTHDESK_ROOT to a valid directory."
            )

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024


def get_settings() -> Settings:
    """Create and validate a Settings instance."""
    settings = Settings()
    return settings
