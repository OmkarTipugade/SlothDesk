"""
Tests for the planner (plan validation) and AI classification service.

All tests mock the Ollama client — no live model is required.
"""
from __future__ import annotations

import json
import os
from unittest.mock import AsyncMock, patch

import pytest

from app.schemas import FileCategory, FileRecord, PlanAction
from app.services.planner import validate_plan
from app.services.ai import classify_files
from app.services.ollama import OllamaClient, OllamaBadResponse


# ── Helpers ─────────────────────────────────────────────────────


def _make_inventory(root: str) -> list:
    """Build a minimal inventory from the test root."""
    files = []
    for name in ["report.pdf", "photo.jpg", "notes.txt", "invoice_2024.pdf", "resume.docx"]:
        path = os.path.join(root, name)
        if os.path.exists(path):
            files.append(FileRecord(
                name=name,
                relative_path=name,
                extension=os.path.splitext(name)[1],
                size_bytes=os.path.getsize(path),
                file_type="document",
            ))
    return files


def _action(source: str, dest: str, category: str = "Documents", reason: str = "test") -> PlanAction:
    return PlanAction(source=source, destination=dest, category=category, reason=reason)


# ── Plan Validation Tests ───────────────────────────────────────


class TestValidatePlan:
    """Tests for planner.validate_plan."""

    def test_valid_action_passes(self, tmp_root):
        inventory = _make_inventory(tmp_root)
        actions = [_action("report.pdf", "Documents/report.pdf")]
        valid, rejected = validate_plan(actions, inventory, tmp_root)
        assert len(valid) == 1
        assert len(rejected) == 0

    def test_rejects_absolute_path_source(self, tmp_root):
        inventory = _make_inventory(tmp_root)
        actions = [_action("/etc/passwd", "Documents/passwd")]
        valid, rejected = validate_plan(actions, inventory, tmp_root)
        assert len(valid) == 0
        assert len(rejected) == 1
        assert "Absolute" in rejected[0]["reason"] or "Invalid" in rejected[0]["reason"]

    def test_rejects_absolute_path_destination(self, tmp_root):
        inventory = _make_inventory(tmp_root)
        actions = [_action("report.pdf", "/tmp/report.pdf")]
        valid, rejected = validate_plan(actions, inventory, tmp_root)
        assert len(valid) == 0
        assert len(rejected) == 1

    def test_rejects_traversal_in_source(self, tmp_root):
        inventory = _make_inventory(tmp_root)
        actions = [_action("../../../etc/passwd", "Documents/passwd")]
        valid, rejected = validate_plan(actions, inventory, tmp_root)
        assert len(valid) == 0
        assert any("traversal" in r["reason"].lower() or "invalid" in r["reason"].lower() for r in rejected)

    def test_rejects_traversal_in_destination(self, tmp_root):
        inventory = _make_inventory(tmp_root)
        actions = [_action("report.pdf", "../outside/report.pdf")]
        valid, rejected = validate_plan(actions, inventory, tmp_root)
        assert len(valid) == 0

    def test_rejects_invalid_category(self, tmp_root):
        inventory = _make_inventory(tmp_root)
        actions = [_action("report.pdf", "Malware/report.pdf", category="Malware")]
        valid, rejected = validate_plan(actions, inventory, tmp_root)
        assert len(valid) == 0
        assert any("category" in r["reason"].lower() for r in rejected)

    def test_rejects_nonexistent_source(self, tmp_root):
        inventory = _make_inventory(tmp_root)
        actions = [_action("does_not_exist.txt", "Documents/does_not_exist.txt")]
        valid, rejected = validate_plan(actions, inventory, tmp_root)
        assert len(valid) == 0
        assert any("inventory" in r["reason"].lower() or "not in" in r["reason"].lower() for r in rejected)

    def test_rejects_duplicate_sources(self, tmp_root):
        inventory = _make_inventory(tmp_root)
        actions = [
            _action("report.pdf", "Documents/report.pdf"),
            _action("report.pdf", "Invoices/report.pdf"),
        ]
        valid, rejected = validate_plan(actions, inventory, tmp_root)
        assert len(valid) == 1
        assert len(rejected) == 1
        assert any("duplicate" in r["reason"].lower() for r in rejected)

    def test_rejects_duplicate_destinations(self, tmp_root):
        inventory = _make_inventory(tmp_root)
        actions = [
            _action("report.pdf", "Documents/same_name.pdf"),
            _action("invoice_2024.pdf", "Documents/same_name.pdf", category="Invoices"),
        ]
        valid, rejected = validate_plan(actions, inventory, tmp_root)
        assert len(valid) == 1
        assert len(rejected) == 1

    def test_rejects_noop_move(self, tmp_root):
        inventory = _make_inventory(tmp_root)
        actions = [_action("report.pdf", "report.pdf")]
        valid, rejected = validate_plan(actions, inventory, tmp_root)
        assert len(valid) == 0
        assert any("identical" in r["reason"].lower() for r in rejected)

    def test_rejects_existing_destination(self, tmp_root):
        inventory = _make_inventory(tmp_root)
        # notes.txt already exists at root
        actions = [_action("report.pdf", "notes.txt")]
        valid, rejected = validate_plan(actions, inventory, tmp_root)
        assert len(valid) == 0
        assert any("exists" in r["reason"].lower() for r in rejected)

    def test_rejects_extension_change(self, tmp_root):
        inventory = _make_inventory(tmp_root)
        actions = [_action("report.pdf", "Documents/report.exe")]
        valid, rejected = validate_plan(actions, inventory, tmp_root)
        assert len(valid) == 0
        assert any("extension" in r["reason"].lower() for r in rejected)

    def test_all_valid_categories_accepted(self, tmp_root):
        """Every FileCategory value should be accepted."""
        inventory = _make_inventory(tmp_root)
        for cat in FileCategory:
            actions = [_action("report.pdf", f"{cat.value}/report.pdf", category=cat.value)]
            valid, _ = validate_plan(actions, inventory, tmp_root)
            assert len(valid) == 1, f"Category {cat.value} was rejected"

    def test_bounds_max_actions(self, tmp_root):
        inventory = _make_inventory(tmp_root)
        # Create more actions than max_actions
        actions = [_action("report.pdf", f"Documents/report_{i}.pdf") for i in range(200)]
        valid, rejected = validate_plan(actions, inventory, tmp_root, max_actions=5)
        # At most 5 should be considered (first gets accepted, rest are duplicate sources)
        assert len(valid) <= 5

    def test_rejects_symlink_source(self, tmp_root):
        inventory = _make_inventory(tmp_root)
        link_path = os.path.join(tmp_root, "link_file.txt")
        target_path = os.path.join(tmp_root, "notes.txt")
        try:
            os.symlink(target_path, link_path)
        except OSError:
            pytest.skip("Cannot create symlinks on this system")

        # Add the symlink to inventory manually
        inventory.append(FileRecord(
            name="link_file.txt", relative_path="link_file.txt",
            extension=".txt", size_bytes=10, file_type="document",
        ))
        actions = [_action("link_file.txt", "Documents/link_file.txt")]
        valid, rejected = validate_plan(actions, inventory, tmp_root)
        assert len(valid) == 0
        assert any("symlink" in r["reason"].lower() for r in rejected)


# ── AI Classification Tests (mocked) ───────────────────────────


class TestClassifyFiles:
    """Tests for ai.classify_files with mocked Ollama."""

    @pytest.mark.asyncio
    async def test_successful_classification(self, tmp_root):
        """Mock a valid structured response from Ollama."""
        inventory = _make_inventory(tmp_root)
        mock_response = json.dumps({
            "actions": [
                {
                    "source": "report.pdf",
                    "destination": "Documents/report.pdf",
                    "category": "Documents",
                    "reason": "PDF document",
                },
            ]
        })

        client = OllamaClient("http://localhost:11434", "qwen3:4b")
        with patch.object(client, "chat", new_callable=AsyncMock, return_value=mock_response):
            result = await classify_files(client, inventory)

        assert len(result) == 1
        assert result[0].source == "report.pdf"
        assert result[0].category == "Documents"

    @pytest.mark.asyncio
    async def test_empty_file_list(self):
        """No files means no actions."""
        client = OllamaClient("http://localhost:11434", "qwen3:4b")
        result = await classify_files(client, [])
        assert result == []

    @pytest.mark.asyncio
    async def test_malformed_json_response(self, tmp_root):
        """Model returns invalid JSON — should raise after retries."""
        inventory = _make_inventory(tmp_root)

        client = OllamaClient("http://localhost:11434", "qwen3:4b")
        with patch.object(client, "chat", new_callable=AsyncMock, return_value="not valid json {{{"):
            with pytest.raises(OllamaBadResponse):
                await classify_files(client, inventory, max_retries=0)

    @pytest.mark.asyncio
    async def test_missing_actions_field(self, tmp_root):
        """Model returns JSON without the required 'actions' key."""
        inventory = _make_inventory(tmp_root)

        client = OllamaClient("http://localhost:11434", "qwen3:4b")
        with patch.object(client, "chat", new_callable=AsyncMock, return_value='{"result": []}'):
            with pytest.raises(OllamaBadResponse):
                await classify_files(client, inventory, max_retries=0)

    @pytest.mark.asyncio
    async def test_retries_on_bad_output(self, tmp_root):
        """Model produces bad output first, valid output on retry."""
        inventory = _make_inventory(tmp_root)
        good = json.dumps({
            "actions": [{
                "source": "report.pdf",
                "destination": "Documents/report.pdf",
                "category": "Documents",
                "reason": "doc",
            }]
        })

        client = OllamaClient("http://localhost:11434", "qwen3:4b")
        with patch.object(
            client, "chat", new_callable=AsyncMock,
            side_effect=["broken json {", good],
        ):
            result = await classify_files(client, inventory, max_retries=1)
            assert len(result) == 1

    @pytest.mark.asyncio
    async def test_empty_actions_from_model(self, tmp_root):
        """Model correctly returns no actions when files are already organized."""
        inventory = _make_inventory(tmp_root)

        client = OllamaClient("http://localhost:11434", "qwen3:4b")
        with patch.object(client, "chat", new_callable=AsyncMock, return_value='{"actions": []}'):
            result = await classify_files(client, inventory)
            assert result == []
