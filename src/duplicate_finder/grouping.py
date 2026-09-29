"""Multi-stage duplicate detection."""

from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from duplicate_finder.config import ScanOptions
from duplicate_finder.hasher import hash_file
from duplicate_finder.models import DuplicateGroup, ScannedFile, ScanResult, ScanStatistics
from duplicate_finder.scanner import discover_files


def scan_directory(root: Path, options: ScanOptions | None = None) -> ScanResult:
    options = options or ScanOptions()
    root = root.expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError(f"Not a directory: {root}")
    errors: list[str] = []
    by_size: dict[int, list[ScannedFile]] = defaultdict(list)
    file_count = total_size = 0
    for file in discover_files(root, options, errors.append):
        file_count += 1
        total_size += file.size
        by_size[file.size].append(file)
    candidates = [file for files in by_size.values() if len(files) > 1 for file in files]
    by_digest: dict[tuple[int, str], list[ScannedFile]] = defaultdict(list)
    with ThreadPoolExecutor(max_workers=options.workers) as pool:
        jobs = {pool.submit(hash_file, file.path, options.chunk_size): file for file in candidates}
        for job in as_completed(jobs):
            file = jobs[job]
            try:
                digest = job.result()
                current = file.path.stat()
                if current.st_size != file.size or current.st_mtime_ns != file.modified_ns:
                    errors.append(f"{file.path}: changed during scanning")
                    continue
                by_digest[(file.size, digest)].append(replace(file, sha256=digest))
            except OSError as exc:
                errors.append(f"{file.path}: {exc}")
    groups = tuple(
        DuplicateGroup(size, digest, tuple(sorted(files, key=lambda f: str(f.path).casefold())))
        for (size, digest), files in by_digest.items()
        if len(files) > 1
    )
    groups = tuple(
        sorted(groups, key=lambda group: (str(group.files[0].path).casefold(), group.sha256))
    )
    statistics = ScanStatistics(
        file_count,
        total_size,
        len(groups),
        sum(len(group.files) for group in groups),
        sum(group.savings for group in groups),
    )
    return ScanResult(root, datetime.now(UTC), statistics, groups, tuple(errors))
