import json
import os
from collections.abc import Iterator
from pathlib import Path

import pytest

from duplicate_finder.config import ScanOptions
from duplicate_finder.deletion import execute_plan, make_plan
from duplicate_finder.formatter import export_json
from duplicate_finder.grouping import scan_directory


def test_empty_and_one_file(tmp_path: Path) -> None:
    assert scan_directory(tmp_path).statistics.file_count == 0
    (tmp_path / "one.txt").write_text("only", encoding="utf-8")
    result = scan_directory(tmp_path)
    assert result.statistics.file_count == 1
    assert result.groups == ()


def test_sizes_contents_and_names(tmp_path: Path) -> None:
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    (tmp_path / "a" / "same.txt").write_bytes(b"aa")
    (tmp_path / "b" / "same.txt").write_bytes(b"bb")
    (tmp_path / "other").write_bytes(b"longer")
    assert scan_directory(tmp_path).groups == ()
    (tmp_path / "copy").write_bytes(b"aa")
    result = scan_directory(tmp_path)
    assert len(result.groups) == 1
    assert result.groups[0].size == 2
    assert result.statistics.potential_savings == 2


def test_nested_unicode_spaces_empty_and_hidden(tmp_path: Path) -> None:
    nested = tmp_path / "space dir"
    nested.mkdir()
    (nested / "файл.txt").write_bytes(b"")
    (tmp_path / "other empty").write_bytes(b"")
    (tmp_path / ".hidden").write_bytes(b"")
    result = scan_directory(tmp_path)
    assert result.statistics.file_count == 2
    assert len(result.groups[0].files) == 2
    assert scan_directory(tmp_path, ScanOptions(hidden=True)).statistics.file_count == 3


def test_exclude_and_size_bounds(tmp_path: Path) -> None:
    (tmp_path / "a.tmp").write_bytes(b"aaa")
    (tmp_path / "b.txt").write_bytes(b"aaa")
    (tmp_path / "c.txt").write_bytes(b"x")
    result = scan_directory(tmp_path, ScanOptions(min_size=2, max_size=3, exclude=("*.tmp",)))
    assert result.statistics.file_count == 1


def test_missing_file_during_hash_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "a").write_bytes(b"x")
    (tmp_path / "b").write_bytes(b"x")

    def disappearing(path: Path, chunk_size: int) -> str:
        if path.name == "b":
            path.unlink()
        return "0" * 64

    monkeypatch.setattr("duplicate_finder.grouping.hash_file", disappearing)
    result = scan_directory(tmp_path)
    assert result.errors
    assert result.groups == ()


def test_deletion_dry_run_and_keeper(tmp_path: Path) -> None:
    for name in ("a", "b", "c"):
        (tmp_path / name).write_bytes(b"same")
    group = scan_directory(tmp_path).groups[0]
    plan = make_plan(group, 1)
    proposed, failures = execute_plan(plan, dry_run=True)
    assert len(proposed) == 2 and not failures
    assert len(list(tmp_path.iterdir())) == 3
    removed, failures = execute_plan(plan)
    assert len(removed) == 2 and not failures
    assert plan.keep.path.exists()


def test_deletion_rechecks_changed_target(tmp_path: Path) -> None:
    for name in ("a", "b"):
        (tmp_path / name).write_bytes(b"same")
    plan = make_plan(scan_directory(tmp_path).groups[0])
    plan.delete[0].path.write_bytes(b"changed")
    removed, failures = execute_plan(plan)
    assert not removed and failures
    assert plan.keep.path.exists() and plan.delete[0].path.exists()


def test_deletion_stops_when_keeper_changes(tmp_path: Path) -> None:
    for name in ("a", "b", "c"):
        (tmp_path / name).write_bytes(b"same")
    plan = make_plan(scan_directory(tmp_path).groups[0])
    plan.keep.path.write_bytes(b"different")
    removed, failures = execute_plan(plan)
    assert not removed and failures
    assert all(file.path.exists() for file in plan.group.files)


def test_inaccessible_subdirectory_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    blocked = tmp_path / "blocked"
    blocked.mkdir()
    (tmp_path / "readable").write_bytes(b"data")
    original = os.scandir

    def guarded(path: str | os.PathLike[str]) -> Iterator[os.DirEntry[str]]:
        if Path(path) == blocked:
            raise PermissionError("access denied")
        return original(path)

    monkeypatch.setattr("duplicate_finder.scanner.os.scandir", guarded)
    result = scan_directory(tmp_path)
    assert result.statistics.file_count == 1
    assert any("access denied" in error for error in result.errors)


def test_export(tmp_path: Path) -> None:
    (tmp_path / "a").write_bytes(b"same")
    (tmp_path / "b").write_bytes(b"same")
    output = tmp_path / "report.json"
    export_json(scan_directory(tmp_path), output)
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["duplicate_group_count"] == 1
    assert data["duplicate_groups"][0]["files"][0]["sha256"]


def test_invalid_path(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        scan_directory(tmp_path / "missing")
