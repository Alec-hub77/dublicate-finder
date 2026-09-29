"""Rich reports and JSON serialization."""

import json
from pathlib import Path

from rich.console import Console
from rich.table import Table

from duplicate_finder.models import DuplicateGroup, ScanResult


def show_groups(console: Console, groups: tuple[DuplicateGroup, ...]) -> None:
    for index, group in enumerate(groups, 1):
        console.print(
            f"[bold]Group #{index}[/bold]  Size: {group.size:,} bytes  SHA-256: {group.sha256}"
        )
        for file in group.files:
            console.print(f"  {file.path}")


def show_result(console: Console, result: ScanResult, *, groups_only: bool = False) -> None:
    if not groups_only:
        stats = result.statistics
        table = Table(title="Duplicate Finder", show_header=False)
        table.add_column("Metric")
        table.add_column("Value", justify="right")
        for label, value in (
            ("Scanning", str(result.root)),
            ("Files scanned", f"{stats.file_count:,}"),
            ("Total size", f"{stats.total_size:,} bytes"),
            ("Duplicate groups", f"{stats.duplicate_group_count:,}"),
            ("Duplicate files", f"{stats.duplicate_file_count:,}"),
            ("Potential savings", f"{stats.potential_savings:,} bytes"),
        ):
            table.add_row(label, value)
        console.print(table)
    show_groups(console, result.groups)
    if groups_only and not result.groups:
        console.print("No duplicate groups found.")
    for error in result.errors:
        Console(stderr=True).print(f"[yellow]Warning:[/yellow] {error}")


def export_json(result: ScanResult, output: Path) -> None:
    stats = result.statistics
    document = {
        "scan_path": str(result.root),
        "scan_timestamp": result.scanned_at.isoformat(),
        "number_of_files": stats.file_count,
        "total_size": stats.total_size,
        "duplicate_group_count": stats.duplicate_group_count,
        "duplicate_file_count": stats.duplicate_file_count,
        "potential_savings": stats.potential_savings,
        "duplicate_groups": [
            {
                "size": group.size,
                "sha256": group.sha256,
                "files": [
                    {"path": str(file.path), "size": file.size, "sha256": file.sha256}
                    for file in group.files
                ],
            }
            for group in result.groups
        ],
        "errors": list(result.errors),
    }
    output.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
