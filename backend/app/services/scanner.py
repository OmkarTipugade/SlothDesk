"""
SlothDesk file scanner.

Scans the configured root directory and returns file metadata without
modifying files or reading their contents (unless explicitly asked for
duplicate detection).
"""
from __future__ import annotations

import hashlib
import logging
import os
from typing import Dict, List, Optional, Set

from app.schemas import DuplicateGroup, FileRecord

logger = logging.getLogger(__name__)

# Directories always excluded from scanning.
_EXCLUDED_DIRS: Set[str] = frozenset({
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
    ".slothdesk_data",
    ".DS_Store",
})

# File-type mapping based on extension.  Keeps scanning fast by avoiding
# magic-byte inspection.
_TYPE_MAP: Dict[str, str] = {
    # Documents
    ".pdf": "document",
    ".doc": "document",
    ".docx": "document",
    ".txt": "document",
    ".rtf": "document",
    ".odt": "document",
    ".md": "document",
    ".tex": "document",
    ".csv": "document",
    ".tsv": "document",
    ".xls": "document",
    ".xlsx": "document",
    # Images
    ".jpg": "image",
    ".jpeg": "image",
    ".png": "image",
    ".gif": "image",
    ".webp": "image",
    ".svg": "image",
    ".bmp": "image",
    ".tiff": "image",
    ".ico": "image",
    ".heic": "image",
    # Audio
    ".mp3": "audio",
    ".wav": "audio",
    ".flac": "audio",
    ".aac": "audio",
    ".ogg": "audio",
    ".oga": "audio",
    ".m4a": "audio",
    ".wma": "audio",
    ".aiff": "audio",
    ".aif": "audio",
    ".alac": "audio",
    ".opus": "audio",
    ".mid": "audio",
    ".midi": "audio",
    ".amr": "audio",
    ".ape": "audio",
    ".ac3": "audio",
    ".pcm": "audio",
    # Video
    ".mp4": "video",
    ".m4v": "video",
    ".mkv": "video",
    ".avi": "video",
    ".mov": "video",
    ".wmv": "video",
    ".webm": "video",
    ".flv": "video",
    ".f4v": "video",
    ".mpg": "video",
    ".mpeg": "video",
    ".m2v": "video",
    ".3gp": "video",
    ".3g2": "video",
    ".ts": "video",
    ".mts": "video",
    ".m2ts": "video",
    ".vob": "video",
    ".ogv": "video",
    ".divx": "video",
    # Archives
    ".zip": "archive",
    ".tar": "archive",
    ".gz": "archive",
    ".bz2": "archive",
    ".rar": "archive",
    ".7z": "archive",
    # Code / config / data
    ".py": "code",
    ".js": "code",
    ".jsx": "code",
    ".ts": "code",
    ".tsx": "code",
    ".html": "code",
    ".css": "code",
    ".cpp": "code",
    ".c": "code",
    ".java": "code",
    ".kt": "code",
    ".rs": "code",
    ".go": "code",
    ".rb": "code",
    ".php": "code",
    ".sql": "data",
    ".json": "data",
    ".yaml": "data",
    ".yml": "data",
    ".xml": "data",
    ".toml": "data",
    ".ini": "data",
}


def _detect_file_type(extension: str) -> str:
    """Map extension to a high-level type string."""
    return _TYPE_MAP.get(extension.lower(), "other")


def scan_directory(
    root: str,
    max_files: int = 500,
    max_file_size_bytes: Optional[int] = None,
) -> List[FileRecord]:
    """
    Scan *root* non-recursively into subdirectories and return sorted
    file metadata.

    Rules:
    - Excludes hidden files and directories (names starting with '.').
    - Excludes well-known non-user directories (.git, .venv, etc.).
    - Skips symbolic links.
    - Skips unreadable entries.
    - Never modifies files.
    - Returns deterministic results sorted by relative_path.
    - Stops after *max_files* entries.
    """
    if not os.path.isdir(root):
        raise FileNotFoundError(f"Scan root does not exist: {root!r}")

    real_root = os.path.realpath(root)
    files: List[FileRecord] = []
    count = 0

    for dirpath, dirnames, filenames in os.walk(real_root, followlinks=False):
        # Prune excluded and hidden directories in-place so os.walk skips them
        dirnames[:] = [
            d for d in dirnames
            if d not in _EXCLUDED_DIRS and not d.startswith(".")
        ]
        dirnames.sort()  # deterministic traversal order

        for filename in sorted(filenames):
            if count >= max_files:
                break

            # Skip hidden files
            if filename.startswith("."):
                continue

            full_path = os.path.join(dirpath, filename)

            # Skip symlinks
            if os.path.islink(full_path):
                logger.debug("Skipping symlink: %s", full_path)
                continue

            # Ensure the file is within the root (paranoid check)
            real_path = os.path.realpath(full_path)
            if not real_path.startswith(real_root + os.sep) and real_path != real_root:
                logger.warning("File escapes root, skipping: %s", full_path)
                continue

            try:
                stat = os.stat(full_path)
            except OSError as exc:
                logger.warning("Cannot stat %s: %s", full_path, exc)
                continue

            if not os.path.isfile(full_path):
                continue

            relative = os.path.relpath(full_path, real_root)
            extension = os.path.splitext(filename)[1].lower()

            files.append(FileRecord(
                name=filename,
                relative_path=relative,
                extension=extension,
                size_bytes=stat.st_size,
                last_modified=stat.st_mtime,
                file_type=_detect_file_type(extension),
            ))
            count += 1

        if count >= max_files:
            break

    # Sort by relative path for deterministic output
    files.sort(key=lambda f: f.relative_path)
    return files


def compute_file_hash(path: str, chunk_size: int = 8192) -> str:
    """
    Compute SHA-256 hash of a file incrementally.

    Never loads the entire file into memory.
    """
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def find_duplicates(
    root: str,
    max_files: int = 500,
    max_file_size_bytes: Optional[int] = None,
) -> List[DuplicateGroup]:
    """
    Identify duplicate files by SHA-256 hash.

    Two-pass approach:
    1. Group files by size (only files with matching sizes can be duplicates).
    2. Hash files in each size group and collect actual duplicates.

    Never deletes anything.
    """
    files = scan_directory(root, max_files=max_files, max_file_size_bytes=max_file_size_bytes)
    real_root = os.path.realpath(root)

    # First pass: group by size
    size_groups: Dict[int, List[FileRecord]] = {}
    for f in files:
        if f.size_bytes == 0:
            continue  # Skip empty files
        size_groups.setdefault(f.size_bytes, []).append(f)

    # Second pass: hash files that share a size
    hash_groups: Dict[str, List[FileRecord]] = {}
    for size, group in size_groups.items():
        if len(group) < 2:
            continue

        if max_file_size_bytes and size > max_file_size_bytes:
            continue

        for f in group:
            full_path = os.path.join(real_root, f.relative_path)
            try:
                file_hash = compute_file_hash(full_path)
                hash_groups.setdefault(file_hash, []).append(f)
            except OSError as exc:
                logger.warning("Cannot hash %s: %s", full_path, exc)

    # Build results: only groups with 2+ files
    duplicates: List[DuplicateGroup] = []
    for file_hash, group in sorted(hash_groups.items()):
        if len(group) >= 2:
            duplicates.append(DuplicateGroup(
                hash=file_hash,
                size_bytes=group[0].size_bytes,
                paths=[f.relative_path for f in group],
            ))

    return duplicates
