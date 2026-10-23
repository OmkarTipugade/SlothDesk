"""
Tests for the file scanner service.
"""
from __future__ import annotations

import os

from app.services.scanner import scan_directory, find_duplicates, compute_file_hash


class TestScanDirectory:
    """Tests for scanner.scan_directory."""

    def test_scans_files_in_root(self, tmp_root):
        files = scan_directory(tmp_root)
        names = {f.name for f in files}
        assert "report.pdf" in names
        assert "photo.jpg" in names
        assert "notes.txt" in names

    def test_returns_file_metadata(self, tmp_root):
        files = scan_directory(tmp_root)
        pdf = next(f for f in files if f.name == "report.pdf")
        assert pdf.extension == ".pdf"
        assert pdf.size_bytes > 0
        assert pdf.relative_path == "report.pdf"
        assert pdf.file_type == "document"

    def test_excludes_hidden_files(self, tmp_root):
        files = scan_directory(tmp_root)
        names = {f.name for f in files}
        assert ".hidden_file" not in names

    def test_excludes_git_directory(self, tmp_root):
        files = scan_directory(tmp_root)
        paths = {f.relative_path for f in files}
        for p in paths:
            assert ".git" not in p

    def test_excludes_pycache_directory(self, tmp_root):
        files = scan_directory(tmp_root)
        paths = {f.relative_path for f in files}
        for p in paths:
            assert "__pycache__" not in p

    def test_excludes_node_modules(self, tmp_root):
        files = scan_directory(tmp_root)
        paths = {f.relative_path for f in files}
        for p in paths:
            assert "node_modules" not in p

    def test_scans_subdirectories(self, tmp_root):
        files = scan_directory(tmp_root)
        paths = {f.relative_path for f in files}
        expected = os.path.join("subfolder", "nested.md")
        assert expected in paths

    def test_results_sorted_by_path(self, tmp_root):
        files = scan_directory(tmp_root)
        paths = [f.relative_path for f in files]
        assert paths == sorted(paths)

    def test_respects_max_files_limit(self, tmp_root):
        files = scan_directory(tmp_root, max_files=2)
        assert len(files) <= 2

    def test_skips_symlinks(self, tmp_root):
        # Create a symlink
        target = os.path.join(tmp_root, "report.pdf")
        link = os.path.join(tmp_root, "link_to_report.pdf")
        try:
            os.symlink(target, link)
        except OSError:
            # Symlink creation may fail on some systems
            return

        files = scan_directory(tmp_root)
        names = {f.name for f in files}
        assert "link_to_report.pdf" not in names

    def test_handles_nonexistent_root(self):
        import pytest
        with pytest.raises(FileNotFoundError):
            scan_directory("/nonexistent/path/that/does/not/exist")

    def test_handles_empty_directory(self, tmp_path):
        empty = str(tmp_path / "empty")
        os.makedirs(empty)
        files = scan_directory(empty)
        assert files == []

    def test_deterministic_results(self, tmp_root):
        """Two consecutive scans return the same results."""
        first = scan_directory(tmp_root)
        second = scan_directory(tmp_root)
        assert [f.relative_path for f in first] == [f.relative_path for f in second]


class TestComputeFileHash:
    """Tests for SHA-256 hashing."""

    def test_hash_is_consistent(self, tmp_root):
        path = os.path.join(tmp_root, "report.pdf")
        h1 = compute_file_hash(path)
        h2 = compute_file_hash(path)
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 hex digest

    def test_different_files_different_hashes(self, tmp_root):
        h1 = compute_file_hash(os.path.join(tmp_root, "report.pdf"))
        h2 = compute_file_hash(os.path.join(tmp_root, "notes.txt"))
        assert h1 != h2


class TestFindDuplicates:
    """Tests for duplicate detection."""

    def test_no_duplicates_in_unique_files(self, tmp_root):
        groups = find_duplicates(tmp_root)
        # Our test files have unique content
        assert len(groups) == 0

    def test_detects_duplicates(self, tmp_path):
        root = str(tmp_path / "dup_test")
        os.makedirs(root)

        content = b"identical content here"
        with open(os.path.join(root, "file_a.txt"), "wb") as f:
            f.write(content)
        with open(os.path.join(root, "file_b.txt"), "wb") as f:
            f.write(content)
        with open(os.path.join(root, "unique.txt"), "wb") as f:
            f.write(b"different content")

        groups = find_duplicates(root)
        assert len(groups) == 1
        assert len(groups[0].paths) == 2
        assert set(groups[0].paths) == {"file_a.txt", "file_b.txt"}
