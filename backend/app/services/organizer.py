"""
SlothDesk safe file organizer.

Moves files only after full validation and explicit user confirmation.
Uses a two-phase approach (validate-all-then-execute) with partial
rollback on failure.

KNOWN LIMITATIONS:
- Filesystem operations are not truly atomic.  A crash between moves
  leaves some files moved and others in their original locations.
- Concurrent modifications by other processes between validation and
  execution may cause unexpected results.  We mitigate this with
  re-validation immediately before each move.
- Cross-filesystem moves use shutil.move which copies then deletes;
  this is not atomic.
- Rollback is best-effort.  If a rollback move fails, the error is
  reported but the file remains in its new location.
"""
from __future__ import annotations

import logging
import os
import shutil
import uuid
from typing import Dict, List, Optional, Tuple

from app.schemas import ActionResult, OperationStatus, PlanAction
from app.security.paths import reject_symlink, resolve_within_root
from app.services.scanner import compute_file_hash

logger = logging.getLogger(__name__)


class OrganizeError(Exception):
    """Raised when the organizer rejects the request before execution."""
    pass


def _fingerprint(path: str) -> Optional[str]:
    """Compute a SHA-256 fingerprint for change detection."""
    try:
        return compute_file_hash(path)
    except OSError:
        return None


def validate_and_execute(
    actions: List[PlanAction],
    confirmed: bool,
    root: str,
) -> Tuple[str, List[ActionResult]]:
    """
    Validate then execute a batch of file moves.

    Parameters
    ----------
    actions : list of PlanAction from the validated plan
    confirmed : must be True; rejected otherwise
    root : the absolute path to the permitted root directory

    Returns
    -------
    (operation_id, results) where results contains per-action status.

    Raises
    ------
    OrganizeError if the request is rejected before execution begins.
    """
    operation_id = uuid.uuid4().hex[:12]
    real_root = os.path.realpath(root)

    # ── Gate: confirmation required ─────────────────────────────
    if not confirmed:
        raise OrganizeError("Explicit confirmation required. Set confirmed=true.")

    if not actions:
        raise OrganizeError("No actions provided.")

    # ── Phase 1: Validate entire batch ──────────────────────────
    validated: List[Dict[str, str]] = []
    results: List[ActionResult] = []
    seen_sources: set = set()
    seen_destinations: set = set()

    for action in actions:
        source = action.source
        destination = action.destination

        # Resolve paths
        src_abs = resolve_within_root(real_root, source)
        dst_abs = resolve_within_root(real_root, destination)

        if src_abs is None:
            results.append(ActionResult(
                source=source, destination=destination,
                status=OperationStatus.SKIPPED,
                error="Source path is invalid or escapes root",
            ))
            continue

        if dst_abs is None:
            results.append(ActionResult(
                source=source, destination=destination,
                status=OperationStatus.SKIPPED,
                error="Destination path is invalid or escapes root",
            ))
            continue

        # Reject symlinks
        if reject_symlink(src_abs):
            results.append(ActionResult(
                source=source, destination=destination,
                status=OperationStatus.SKIPPED,
                error="Source is or contains a symlink",
            ))
            continue

        # Source must exist and be a regular file
        if not os.path.isfile(src_abs):
            results.append(ActionResult(
                source=source, destination=destination,
                status=OperationStatus.SKIPPED,
                error="Source file does not exist",
            ))
            continue

        # Destination must not exist
        if os.path.exists(dst_abs):
            results.append(ActionResult(
                source=source, destination=destination,
                status=OperationStatus.SKIPPED,
                error="Destination already exists",
            ))
            continue

        # Duplicate source
        if source in seen_sources:
            results.append(ActionResult(
                source=source, destination=destination,
                status=OperationStatus.SKIPPED,
                error="Duplicate source in batch",
            ))
            continue

        # Duplicate destination
        if destination in seen_destinations:
            results.append(ActionResult(
                source=source, destination=destination,
                status=OperationStatus.SKIPPED,
                error="Duplicate destination in batch",
            ))
            continue

        # Fingerprint the source for later change detection
        fingerprint = _fingerprint(src_abs)

        seen_sources.add(source)
        seen_destinations.add(destination)
        validated.append({
            "source": source,
            "destination": destination,
            "src_abs": src_abs,
            "dst_abs": dst_abs,
            "fingerprint": fingerprint,
            "category": action.category,
        })

    if not validated:
        # All actions were rejected during validation
        return operation_id, results

    # ── Phase 2: Execute moves ──────────────────────────────────
    completed_moves: List[Tuple[str, str]] = []  # (dst_abs, src_abs) for rollback

    for entry in validated:
        src_abs = entry["src_abs"]
        dst_abs = entry["dst_abs"]
        source = entry["source"]
        destination = entry["destination"]
        expected_fp = entry["fingerprint"]

        # Re-validate immediately before move
        if not os.path.isfile(src_abs):
            results.append(ActionResult(
                source=source, destination=destination,
                status=OperationStatus.FAILED,
                error="Source disappeared between validation and execution",
            ))
            continue

        if os.path.exists(dst_abs):
            results.append(ActionResult(
                source=source, destination=destination,
                status=OperationStatus.FAILED,
                error="Destination appeared between validation and execution",
            ))
            continue

        # Detect source changes via fingerprint
        if expected_fp is not None:
            current_fp = _fingerprint(src_abs)
            if current_fp != expected_fp:
                results.append(ActionResult(
                    source=source, destination=destination,
                    status=OperationStatus.FAILED,
                    error="Source file changed between planning and execution",
                ))
                continue

        try:
            # Create destination directory
            dst_dir = os.path.dirname(dst_abs)
            if dst_dir:
                os.makedirs(dst_dir, exist_ok=True)

            # Attempt atomic rename first; fall back to shutil for cross-device
            try:
                os.rename(src_abs, dst_abs)
            except OSError:
                shutil.move(src_abs, dst_abs)

            completed_moves.append((dst_abs, src_abs))
            results.append(ActionResult(
                source=source, destination=destination,
                status=OperationStatus.SUCCESS,
            ))

        except OSError as exc:
            logger.error("Move failed %s -> %s: %s", source, destination, exc)
            results.append(ActionResult(
                source=source, destination=destination,
                status=OperationStatus.FAILED,
                error=f"Move failed: {exc}",
            ))
            # Attempt rollback of this batch
            _rollback(completed_moves, results)
            break

    return operation_id, results


def _rollback(
    completed: List[Tuple[str, str]],
    results: List[ActionResult],
) -> None:
    """
    Best-effort rollback of completed moves.

    Moves files back from destination to source.  Never overwrites an
    existing file during rollback.  Reports failures explicitly.
    """
    for dst_abs, src_abs in reversed(completed):
        if not os.path.exists(dst_abs):
            logger.warning("Rollback skipped — moved file no longer at %s", dst_abs)
            continue

        if os.path.exists(src_abs):
            logger.warning("Rollback skipped — original location occupied: %s", src_abs)
            continue

        try:
            try:
                os.rename(dst_abs, src_abs)
            except OSError:
                shutil.move(dst_abs, src_abs)

            # Update the corresponding result
            for r in results:
                if r.status == OperationStatus.SUCCESS:
                    resolved_dst_check = os.path.normpath(dst_abs)
                    # Mark as rolled back (best effort matching)
                    if not os.path.exists(dst_abs) and os.path.exists(src_abs):
                        r.status = OperationStatus.ROLLED_BACK
                        break

            logger.info("Rolled back: %s -> %s", dst_abs, src_abs)
        except OSError as exc:
            logger.error("Rollback failed %s -> %s: %s", dst_abs, src_abs, exc)
