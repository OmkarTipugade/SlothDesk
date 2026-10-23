"""
SlothDesk test fixtures and configuration.

All tests use temporary directories and an in-memory or temp SQLite database.
No test modifies the user's real files or requires a live Ollama model.
"""
from __future__ import annotations

import os
import tempfile
from typing import Generator

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.database import init_db


@pytest.fixture()
def tmp_root(tmp_path) -> str:
    """Create a temporary root directory with sample files."""
    root = str(tmp_path / "slothdesk_test")
    os.makedirs(root, exist_ok=True)

    # Create sample files
    for name in ["report.pdf", "photo.jpg", "notes.txt", "invoice_2024.pdf", "resume.docx"]:
        path = os.path.join(root, name)
        with open(path, "wb") as f:
            f.write(f"fake content for {name}".encode())

    # Create a hidden file (should be excluded)
    with open(os.path.join(root, ".hidden_file"), "w") as f:
        f.write("hidden")

    # Create excluded directories
    for dirname in [".git", "__pycache__", "node_modules"]:
        dirpath = os.path.join(root, dirname)
        os.makedirs(dirpath, exist_ok=True)
        with open(os.path.join(dirpath, "should_skip.txt"), "w") as f:
            f.write("skip me")

    # Create a subdirectory with files
    subdir = os.path.join(root, "subfolder")
    os.makedirs(subdir, exist_ok=True)
    with open(os.path.join(subdir, "nested.md"), "w") as f:
        f.write("# Nested document")

    return root


@pytest.fixture()
def tmp_db(tmp_path) -> str:
    """Initialize a temp SQLite database and return its path."""
    db_path = str(tmp_path / "test_history.db")
    init_db(db_path)
    return db_path


@pytest.fixture()
def test_settings(tmp_root, tmp_db, monkeypatch) -> Settings:
    """Create Settings pointing to temp directories."""
    monkeypatch.setenv("SLOTHDESK_ROOT", tmp_root)
    monkeypatch.setenv("DATABASE_PATH", tmp_db)
    monkeypatch.setenv("OLLAMA_URL", "http://127.0.0.1:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen3:4b")
    monkeypatch.setenv("OLLAMA_TIMEOUT_SECONDS", "10")
    monkeypatch.setenv("MAX_SCAN_FILES", "500")

    settings = Settings(
        slothdesk_root=tmp_root,
        database_path=tmp_db,
    )
    return settings


@pytest.fixture()
def client(test_settings, monkeypatch) -> TestClient:
    """Create a test client with settings pointing to temp directories."""
    # Patch get_settings to return our test settings
    monkeypatch.setattr("app.config.get_settings", lambda: test_settings)
    monkeypatch.setattr("app.api.routes.get_settings", lambda: test_settings)

    # Re-initialize the database for this test
    init_db(test_settings.database_path)

    # Need to reimport to get the patched app
    from app.main import app
    return TestClient(app)
