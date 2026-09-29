"""Filesystem traversal and metadata discovery."""

import fnmatch
import os
import stat
from collections.abc import Callable, Iterator
from pathlib import Path

from duplicate_finder.config import ScanOptions
from duplicate_finder.models import ScannedFile

ErrorHandler = Callable[[str], None]


def _hidden(path: Path, entry: os.DirEntry[str]) -> bool:
    if entry.name.startswith("."):
        return True
    try:
        return bool(
            entry.stat(follow_symlinks=False).st_file_attributes & stat.FILE_ATTRIBUTE_HIDDEN
        )
    except (AttributeError, OSError):
        return False


def discover_files(
    root: Path, options: ScanOptions, on_error: ErrorHandler
) -> Iterator[ScannedFile]:
    """Yield regular files; never follow directory or file symlinks."""
    pending = [root]
    while pending:
        directory = pending.pop()
        try:
            with os.scandir(directory) as entries:
                children = sorted(entries, key=lambda entry: entry.name.casefold())
        except OSError as exc:
            on_error(f"{directory}: {exc}")
            continue
        for entry in children:
            path = Path(entry.path)
            relative = path.relative_to(root).as_posix()
            if any(
                fnmatch.fnmatch(relative, pattern) or fnmatch.fnmatch(entry.name, pattern)
                for pattern in options.exclude
            ):
                continue
            try:
                if entry.is_symlink() or (not options.hidden and _hidden(path, entry)):
                    continue
                if entry.is_dir(follow_symlinks=False):
                    pending.append(path)
                elif entry.is_file(follow_symlinks=False):
                    info = entry.stat(follow_symlinks=False)
                    if info.st_size >= options.min_size and (
                        options.max_size is None or info.st_size <= options.max_size
                    ):
                        yield ScannedFile(path, info.st_size, modified_ns=info.st_mtime_ns)
            except OSError as exc:
                on_error(f"{path}: {exc}")
