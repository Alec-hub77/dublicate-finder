"""Domain models, independent of the user interface."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class ScannedFile:
    path: Path
    size: int
    sha256: str | None = None
    modified_ns: int = 0


@dataclass(frozen=True)
class DuplicateGroup:
    size: int
    sha256: str
    files: tuple[ScannedFile, ...]

    @property
    def savings(self) -> int:
        return self.size * (len(self.files) - 1)


@dataclass(frozen=True)
class ScanStatistics:
    file_count: int
    total_size: int
    duplicate_group_count: int
    duplicate_file_count: int
    potential_savings: int


@dataclass(frozen=True)
class ScanResult:
    root: Path
    scanned_at: datetime
    statistics: ScanStatistics
    groups: tuple[DuplicateGroup, ...]
    errors: tuple[str, ...] = field(default_factory=tuple)
