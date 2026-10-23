"""
SlothDesk path security utilities.

Every filesystem path the backend touches MUST pass through these checks.
"""
from __future__ import annotations

import os
from pathlib import Path, PurePosixPath
from typing import Optional, Tuple


# Components that must never appear in a relative path.
_FORBIDDEN_COMPONENTS = frozenset({"..", "~"})

# Characters that must never appear in any path component (beyond traversal).
# NUL is always invalid; we also reject backslash to avoid cross-platform issues.
_FORBIDDEN_CHARS = frozenset({"\x00", "\\"})


def resolve_within_root(root: str, relative: str) -> Optional[str]:
    """
    Resolve *relative* against *root* and return the absolute path only
    if it is strictly inside *root*.

    Returns None if the path escapes the root, contains traversal,
    or is otherwise unsafe.
    """
    if not relative or not root:
        return None

    # Reject absolute paths disguised as relative
    if os.path.isabs(relative):
        return None

    # Check every component for forbidden patterns
    parts = PurePosixPath(relative).parts
    for part in parts:
        if part in _FORBIDDEN_COMPONENTS:
            return None
        for ch in _FORBIDDEN_CHARS:
            if ch in part:
                return None

    # Resolve without following symlinks for the candidate, then check containment
    candidate = os.path.normpath(os.path.join(root, relative))
    real_root = os.path.realpath(root)

    # The candidate must start with the root path + separator (or be the root itself)
    if not (candidate == real_root or candidate.startswith(real_root + os.sep)):
        return None

    return candidate


def is_within_root(root: str, path: str) -> bool:
    """Check whether *path* is strictly inside *root* after resolving."""
    real_root = os.path.realpath(root)
    real_path = os.path.realpath(path)
    return real_path.startswith(real_root + os.sep)


def reject_symlink(path: str) -> bool:
    """Return True if *path* is or contains a symlink anywhere in its chain."""
    try:
        # Walk up to check each component
        p = Path(path)
        for parent in [p] + list(p.parents):
            if parent.is_symlink():
                return True
            if str(parent) == parent.root:
                break
        return False
    except (OSError, ValueError):
        return True  # Err on the side of caution


def validate_relative_path(relative: str) -> Tuple[bool, str]:
    """
    Validate a relative path for safety.

    Returns (is_valid, error_message).
    """
    if not relative:
        return False, "Path is empty"

    if os.path.isabs(relative):
        return False, "Absolute paths are not allowed"

    parts = PurePosixPath(relative).parts
    if not parts:
        return False, "Path has no components"

    for part in parts:
        if part in _FORBIDDEN_COMPONENTS:
            return False, f"Path traversal component '{part}' is not allowed"
        for ch in _FORBIDDEN_CHARS:
            if ch in part:
                return False, f"Forbidden character in path component"
        if part.startswith("."):
            return False, f"Hidden path components are not allowed"

    return True, ""


def validate_destination_preserves_extension(source: str, destination: str) -> Tuple[bool, str]:
    """
    Verify that the destination preserves the source file's extension.

    Returns (is_valid, error_message).
    """
    src_ext = os.path.splitext(source)[1].lower()
    dst_ext = os.path.splitext(destination)[1].lower()

    if src_ext and src_ext != dst_ext:
        return False, f"Destination must preserve file extension '{src_ext}'"
    return True, ""
