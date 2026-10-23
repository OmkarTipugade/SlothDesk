"""
Tests for the history service and SQLite persistence.
"""
from __future__ import annotations

from app.schemas import ActionResult, OperationStatus
from app.services.history import record_operations, get_history, get_stats


class TestRecordOperations:
    """Tests for persisting operation results."""

    def test_records_are_persisted(self, tmp_db):
        results = [
            ActionResult(source="a.txt", destination="Documents/a.txt", status=OperationStatus.SUCCESS),
            ActionResult(source="b.txt", destination="Images/b.txt", status=OperationStatus.SKIPPED, error="test skip"),
        ]
        record_operations("op001", results, categories={"a.txt": "Documents", "b.txt": "Images"})

        records, total = get_history()
        assert total == 2
        assert len(records) == 2

    def test_records_ordered_newest_first(self, tmp_db):
        results1 = [ActionResult(source="first.txt", destination="D/first.txt", status=OperationStatus.SUCCESS)]
        results2 = [ActionResult(source="second.txt", destination="D/second.txt", status=OperationStatus.SUCCESS)]

        record_operations("op001", results1, categories={"first.txt": "Documents"})
        record_operations("op002", results2, categories={"second.txt": "Documents"})

        records, _ = get_history()
        assert records[0].source == "second.txt"
        assert records[1].source == "first.txt"

    def test_empty_results(self, tmp_db):
        record_operations("op001", [])
        records, total = get_history()
        assert total == 0


class TestGetHistory:
    """Tests for paginated history retrieval."""

    def test_pagination(self, tmp_db):
        results = [
            ActionResult(source=f"file_{i}.txt", destination=f"D/file_{i}.txt", status=OperationStatus.SUCCESS)
            for i in range(10)
        ]
        record_operations("op001", results)

        # Page 1 with size 3
        records, total = get_history(page=1, page_size=3)
        assert total == 10
        assert len(records) == 3

        # Page 2
        records2, _ = get_history(page=2, page_size=3)
        assert len(records2) == 3
        # Different records
        assert records[0].id != records2[0].id

    def test_page_bounds(self, tmp_db):
        """Page beyond last should return empty."""
        results = [ActionResult(source="a.txt", destination="D/a.txt", status=OperationStatus.SUCCESS)]
        record_operations("op001", results)

        records, total = get_history(page=100, page_size=10)
        assert total == 1
        assert len(records) == 0


class TestGetStats:
    """Tests for aggregate statistics."""

    def test_stats_from_real_data(self, tmp_db):
        results = [
            ActionResult(source="a.txt", destination="D/a.txt", status=OperationStatus.SUCCESS),
            ActionResult(source="b.txt", destination="I/b.txt", status=OperationStatus.SUCCESS),
            ActionResult(source="c.txt", destination="D/c.txt", status=OperationStatus.FAILED, error="oops"),
        ]
        record_operations("op001", results, categories={"a.txt": "Documents", "b.txt": "Images", "c.txt": "Documents"})

        stats = get_stats()
        assert stats["total_operations"] == 3
        assert stats["successful_moves"] == 2
        assert stats["failed_moves"] == 1
        assert "Documents" in stats["categories"]
        assert stats["categories"]["Documents"] == 1  # Only successful ones
        assert stats["categories"]["Images"] == 1

    def test_stats_empty_db(self, tmp_db):
        stats = get_stats()
        assert stats["total_operations"] == 0
        assert stats["successful_moves"] == 0
