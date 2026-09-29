"""Conservative deletion planning and execution."""

from dataclasses import dataclass
from pathlib import Path

from duplicate_finder.hasher import hash_file
from duplicate_finder.models import DuplicateGroup, ScannedFile


@dataclass(frozen=True)
class DeletionPlan:
    group: DuplicateGroup
    keep: ScannedFile
    delete: tuple[ScannedFile, ...]


def make_plan(group: DuplicateGroup, keep_index: int = 0) -> DeletionPlan:
    if not 0 <= keep_index < len(group.files):
        raise ValueError("Keep index is outside the group")
    keep = group.files[keep_index]
    return DeletionPlan(group, keep, tuple(file for file in group.files if file != keep))


def _matches(file: ScannedFile, expected_hash: str) -> bool:
    path: Path = file.path
    if path.is_symlink() or not path.is_file():
        return False
    before = path.stat()
    if before.st_size != file.size or before.st_mtime_ns != file.modified_ns:
        return False
    digest = hash_file(path)
    after = path.stat()
    return (
        digest == expected_hash
        and before.st_size == after.st_size
        and before.st_mtime_ns == after.st_mtime_ns
    )


def execute_plan(plan: DeletionPlan, *, dry_run: bool = False) -> tuple[list[Path], list[str]]:
    """Recheck both copies before each removal; stop if the keeper is invalid."""
    deleted: list[Path] = []
    failures: list[str] = []
    if dry_run:
        return [file.path for file in plan.delete], failures
    for file in plan.delete:
        try:
            if not _matches(plan.keep, plan.group.sha256):
                failures.append(
                    f"{plan.keep.path}: keeper changed or cannot be read; group stopped"
                )
                break
            if not _matches(file, plan.group.sha256):
                failures.append(f"{file.path}: changed or cannot be read; skipped")
                continue
            file.path.unlink()
            deleted.append(file.path)
        except OSError as exc:
            failures.append(f"{file.path}: {exc}")
    return deleted, failures
