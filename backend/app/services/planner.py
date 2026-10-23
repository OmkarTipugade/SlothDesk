"""
SlothDesk plan validation service.

Validates AI-generated plans against the current filesystem state and
security rules.  The model is never trusted to enforce these rules —
every proposed action is checked independently on the server.

This module never modifies files.
"""
from __future__ import annotations

import os
from typing import Dict, List, Set, Tuple

from app.schemas import FileCategory, FileRecord, PlanAction
from app.security.paths import (
    resolve_within_root,
    reject_symlink,
    validate_destination_preserves_extension,
    validate_relative_path,
)


class PlanValidationError(Exception):
    """Raised when the plan contains invalid actions."""

    def __init__(self, message: str, rejected: List[Dict[str, str]]):
        super().__init__(message)
        self.rejected = rejected


def _allowed_categories() -> Set[str]:
    """Return the set of allowed category string values."""
    return {c.value for c in FileCategory}


def validate_plan(
    actions: List[PlanAction],
    inventory: List[FileRecord],
    root: str,
    max_actions: int = 100,
) -> Tuple[List[PlanAction], List[Dict[str, str]]]:
    """
    Validate a list of proposed actions against the filesystem and rules.

    Returns (valid_actions, rejected_actions) where rejected_actions is a
    list of dicts with 'source', 'destination', and 'reason' keys.

    Rules enforced:
    1.  Every source exists within the permitted root.
    2.  Every source appears in the scanned inventory.
    3.  Category is one of the allowed values.
    4.  No absolute paths, traversal, symlinks, or invalid components.
    5.  No duplicate source actions.
    6.  No duplicate destinations.
    7.  No existing destination collisions.
    8.  No no-op moves (source == destination).
    9.  Action count is bounded.
    10. File extensions are preserved.
    """
    allowed = _allowed_categories()
    inventory_paths: Set[str] = {f.relative_path for f in inventory}
    real_root = os.path.realpath(root)

    valid: List[PlanAction] = []
    rejected: List[Dict[str, str]] = []

    seen_sources: Set[str] = set()
    seen_destinations: Set[str] = set()

    if len(actions) > max_actions:
        actions = actions[:max_actions]

    for action in actions:
        source = action.source
        destination = action.destination
        category = action.category

        # ── 1. Validate source path syntax ──────────────────────
        ok, err = validate_relative_path(source)
        if not ok:
            rejected.append({"source": source, "destination": destination, "reason": f"Invalid source: {err}"})
            continue

        # ── 2. Validate destination path syntax ─────────────────
        ok, err = validate_relative_path(destination)
        if not ok:
            rejected.append({"source": source, "destination": destination, "reason": f"Invalid destination: {err}"})
            continue

        # ── 3. Category must be allowed ─────────────────────────
        if category not in allowed:
            rejected.append({"source": source, "destination": destination, "reason": f"Invalid category: {category!r}"})
            continue

        # ── 4. Source must be in inventory ──────────────────────
        if source not in inventory_paths:
            rejected.append({"source": source, "destination": destination, "reason": "Source not in scanned inventory"})
            continue

        # ── 5. Source must resolve within root ──────────────────
        resolved_src = resolve_within_root(real_root, source)
        if resolved_src is None:
            rejected.append({"source": source, "destination": destination, "reason": "Source escapes root directory"})
            continue

        # ── 6. Destination must resolve within root ─────────────
        resolved_dst = resolve_within_root(real_root, destination)
        if resolved_dst is None:
            rejected.append({"source": source, "destination": destination, "reason": "Destination escapes root directory"})
            continue

        # ── 7. Reject symlinks ──────────────────────────────────
        if os.path.exists(resolved_src) and reject_symlink(resolved_src):
            rejected.append({"source": source, "destination": destination, "reason": "Source is or contains a symlink"})
            continue

        # ── 8. No-op check ──────────────────────────────────────
        if source == destination:
            rejected.append({"source": source, "destination": destination, "reason": "Source and destination are identical"})
            continue

        # ── 9. Duplicate source ─────────────────────────────────
        if source in seen_sources:
            rejected.append({"source": source, "destination": destination, "reason": "Duplicate source in plan"})
            continue

        # ── 10. Duplicate destination ───────────────────────────
        if destination in seen_destinations:
            rejected.append({"source": source, "destination": destination, "reason": "Duplicate destination in plan"})
            continue

        # ── 11. Existing destination collision ──────────────────
        if os.path.exists(resolved_dst):
            rejected.append({"source": source, "destination": destination, "reason": "Destination already exists"})
            continue

        # ── 12. Extension preservation ──────────────────────────
        ok, err = validate_destination_preserves_extension(source, destination)
        if not ok:
            rejected.append({"source": source, "destination": destination, "reason": err})
            continue

        # ── 13. Source must actually exist on disk ──────────────
        if not os.path.isfile(resolved_src):
            rejected.append({"source": source, "destination": destination, "reason": "Source file does not exist"})
            continue

        seen_sources.add(source)
        seen_destinations.add(destination)
        valid.append(action)

    return valid, rejected
