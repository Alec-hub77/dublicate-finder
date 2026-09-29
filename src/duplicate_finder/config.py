"""Optional TOML configuration and scan options."""

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

from duplicate_finder.exceptions import ConfigurationError


@dataclass(frozen=True)
class ScanOptions:
    min_size: int = 0
    max_size: int | None = None
    exclude: tuple[str, ...] = ()
    hidden: bool = False
    workers: int = min(8, max(1, os.cpu_count() or 1))
    chunk_size: int = 1024 * 1024

    def __post_init__(self) -> None:
        if self.min_size < 0 or (self.max_size is not None and self.max_size < self.min_size):
            raise ConfigurationError("Invalid size range")
        if self.workers < 1 or self.chunk_size < 1:
            raise ConfigurationError("workers and chunk_size must be positive")


def load_options(path: Path | None) -> ScanOptions:
    if path is None:
        return ScanOptions()
    try:
        with path.open("rb") as stream:
            document = tomllib.load(stream)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ConfigurationError(f"Cannot read configuration: {exc}") from exc
    values = document.get("scan", {})
    if not isinstance(values, dict):
        raise ConfigurationError("[scan] must be a table")
    allowed = {"min_size", "max_size", "exclude", "hidden", "workers", "chunk_size"}
    unknown = set(values) - allowed
    if unknown:
        raise ConfigurationError(f"Unknown scan setting: {', '.join(sorted(unknown))}")
    try:
        exclude = values.get("exclude", [])
        if not isinstance(exclude, list) or not all(isinstance(x, str) for x in exclude):
            raise ValueError("exclude must be a list of strings")
        for key in ("min_size", "workers", "chunk_size"):
            if key in values and type(values[key]) is not int:
                raise ValueError(f"{key} must be an integer")
        if "max_size" in values and type(values["max_size"]) is not int:
            raise ValueError("max_size must be an integer")
        if "hidden" in values and type(values["hidden"]) is not bool:
            raise ValueError("hidden must be a boolean")
        return ScanOptions(
            min_size=values.get("min_size", 0),
            max_size=values.get("max_size"),
            exclude=tuple(exclude),
            hidden=values.get("hidden", False),
            workers=values.get("workers", ScanOptions().workers),
            chunk_size=values.get("chunk_size", 1024 * 1024),
        )
    except (TypeError, ValueError) as exc:
        raise ConfigurationError(f"Invalid configuration: {exc}") from exc
