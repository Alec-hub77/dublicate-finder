import json
from pathlib import Path

from typer.testing import CliRunner

from duplicate_finder.cli import app

runner = CliRunner()


def test_cli_commands(tmp_path: Path) -> None:
    (tmp_path / "a").write_bytes(b"x")
    (tmp_path / "b").write_bytes(b"x")
    scan = runner.invoke(app, ["scan", str(tmp_path)])
    assert scan.exit_code == 0 and "Duplicate groups" in scan.output
    duplicates = runner.invoke(app, ["duplicates", str(tmp_path)])
    assert duplicates.exit_code == 0 and "Group #1" in duplicates.output
    output = tmp_path / "report.json"
    exported = runner.invoke(app, ["export", str(tmp_path), "--output", str(output)])
    assert exported.exit_code == 0
    assert json.loads(output.read_text(encoding="utf-8"))["number_of_files"] == 2
    dry_run = runner.invoke(app, ["delete", str(tmp_path), "--dry-run"])
    assert dry_run.exit_code == 0 and "WOULD DELETE" in dry_run.output
    assert (tmp_path / "a").exists() and (tmp_path / "b").exists()
    deletion = runner.invoke(app, ["delete", str(tmp_path), "--yes"])
    assert deletion.exit_code == 0 and "Deleted:" in deletion.output
    assert sum(path.exists() for path in (tmp_path / "a", tmp_path / "b")) == 1


def test_cli_errors(tmp_path: Path) -> None:
    assert runner.invoke(app, ["scan", str(tmp_path / "missing")]).exit_code == 2
    assert runner.invoke(app, ["scan", str(tmp_path), "--min-size", "-1"]).exit_code == 2
