"""
Tests for the file organizer service.

Uses temporary directories — never modifies real user files.
"""
from __future__ import annotations

import os

import pytest

from app.schemas import PlanAction
from app.services.organizer import validate_and_execute, OrganizeError


def _action(source: str, dest: str, category: str = "Documents") -> PlanAction:
    return PlanAction(source=source, destination=dest, category=category, reason="test")


class TestOrganizerValidation:
    """Tests for organizer validation gates."""

    def test_rejects_without_confirmation(self, tmp_root):
        actions = [_action("report.pdf", "Documents/report.pdf")]
        with pytest.raises(OrganizeError, match="confirmation"):
            validate_and_execute(actions, confirmed=False, root=tmp_root)

    def test_rejects_empty_actions(self, tmp_root):
        with pytest.raises(OrganizeError, match="No actions"):
            validate_and_execute([], confirmed=True, root=tmp_root)

    def test_skips_nonexistent_source(self, tmp_root):
        actions = [_action("nonexistent.txt", "Documents/nonexistent.txt")]
        op_id, results = validate_and_execute(actions, confirmed=True, root=tmp_root)
        assert len(results) == 1
        assert results[0].status.value == "skipped"

    def test_skips_destination_that_exists(self, tmp_root):
        # notes.txt exists; try to move report.pdf to notes.txt
        actions = [_action("report.pdf", "notes.txt")]
        op_id, results = validate_and_execute(actions, confirmed=True, root=tmp_root)
        assert len(results) == 1
        assert results[0].status.value == "skipped"
        assert "exists" in results[0].error.lower()

    def test_skips_duplicate_source(self, tmp_root):
        actions = [
            _action("report.pdf", "Documents/report.pdf"),
            _action("report.pdf", "Invoices/report.pdf"),
        ]
        op_id, results = validate_and_execute(actions, confirmed=True, root=tmp_root)
        success_count = sum(1 for r in results if r.status.value == "success")
        skip_count = sum(1 for r in results if r.status.value == "skipped")
        assert success_count == 1
        assert skip_count == 1

    def test_skips_duplicate_destination(self, tmp_root):
        actions = [
            _action("report.pdf", "Documents/same_dest.pdf"),
            _action("invoice_2024.pdf", "Documents/same_dest.pdf", category="Invoices"),
        ]
        op_id, results = validate_and_execute(actions, confirmed=True, root=tmp_root)
        success_count = sum(1 for r in results if r.status.value == "success")
        skip_count = sum(1 for r in results if r.status.value == "skipped")
        assert success_count == 1
        assert skip_count == 1


class TestOrganizerExecution:
    """Tests for actual file moves."""

    def test_successful_move(self, tmp_root):
        actions = [_action("report.pdf", "Documents/report.pdf")]
        op_id, results = validate_and_execute(actions, confirmed=True, root=tmp_root)

        assert len(results) == 1
        assert results[0].status.value == "success"
        assert op_id  # Should be a non-empty string

        # Verify filesystem state
        assert not os.path.exists(os.path.join(tmp_root, "report.pdf"))
        assert os.path.exists(os.path.join(tmp_root, "Documents", "report.pdf"))

    def test_creates_destination_directory(self, tmp_root):
        actions = [_action("photo.jpg", "Images/photos/photo.jpg", category="Images")]
        op_id, results = validate_and_execute(actions, confirmed=True, root=tmp_root)

        assert results[0].status.value == "success"
        assert os.path.isdir(os.path.join(tmp_root, "Images", "photos"))

    def test_multiple_moves(self, tmp_root):
        actions = [
            _action("report.pdf", "Documents/report.pdf"),
            _action("photo.jpg", "Images/photo.jpg", category="Images"),
            _action("notes.txt", "Notes/notes.txt", category="Notes"),
        ]
        op_id, results = validate_and_execute(actions, confirmed=True, root=tmp_root)

        success = [r for r in results if r.status.value == "success"]
        assert len(success) == 3

    def test_partial_failure_reports_accurately(self, tmp_root):
        """When some actions are valid and some are invalid, report both."""
        actions = [
            _action("report.pdf", "Documents/report.pdf"),
            _action("nonexistent.txt", "Documents/nonexistent.txt"),
        ]
        op_id, results = validate_and_execute(actions, confirmed=True, root=tmp_root)

        statuses = {r.source: r.status.value for r in results}
        assert statuses["report.pdf"] == "success"
        assert statuses["nonexistent.txt"] == "skipped"

    def test_rejects_path_traversal(self, tmp_root):
        actions = [_action("report.pdf", "../outside/report.pdf")]
        op_id, results = validate_and_execute(actions, confirmed=True, root=tmp_root)
        assert len(results) == 1
        assert results[0].status.value == "skipped"
        assert "invalid" in results[0].error.lower() or "escape" in results[0].error.lower()

    def test_rejects_symlink_source(self, tmp_root):
        target = os.path.join(tmp_root, "notes.txt")
        link = os.path.join(tmp_root, "link.txt")
        try:
            os.symlink(target, link)
        except OSError:
            pytest.skip("Cannot create symlinks on this system")

        actions = [_action("link.txt", "Documents/link.txt")]
        op_id, results = validate_and_execute(actions, confirmed=True, root=tmp_root)
        assert results[0].status.value == "skipped"
        assert "symlink" in results[0].error.lower()

    def test_operation_id_is_unique(self, tmp_root):
        actions = [_action("report.pdf", "Documents/report.pdf")]
        op1, _ = validate_and_execute(actions, confirmed=True, root=tmp_root)

        # Recreate the file for second test
        with open(os.path.join(tmp_root, "report2.pdf"), "wb") as f:
            f.write(b"content")
        actions2 = [_action("report2.pdf", "Documents/report2.pdf")]
        op2, _ = validate_and_execute(actions2, confirmed=True, root=tmp_root)

        assert op1 != op2
