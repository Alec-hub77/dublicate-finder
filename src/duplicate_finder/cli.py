"""Command-line interface."""

from dataclasses import replace
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from duplicate_finder.config import ScanOptions, load_options
from duplicate_finder.deletion import execute_plan, make_plan
from duplicate_finder.exceptions import ConfigurationError
from duplicate_finder.formatter import export_json, show_groups, show_result
from duplicate_finder.grouping import scan_directory
from duplicate_finder.models import ScanResult

app = typer.Typer(
    help="Find duplicate files by size and complete SHA-256 hash.", no_args_is_help=True
)
console = Console()
error_console = Console(stderr=True)

Root = Annotated[Path, typer.Argument(help="Directory to scan recursively.")]
Config = Annotated[Path | None, typer.Option("--config", help="Optional TOML configuration.")]
MinSize = Annotated[int | None, typer.Option("--min-size", help="Minimum file size in bytes.")]
MaxSize = Annotated[int | None, typer.Option("--max-size", help="Maximum file size in bytes.")]
Exclude = Annotated[list[str] | None, typer.Option("--exclude", help="Glob to skip; repeatable.")]
Hidden = Annotated[bool | None, typer.Option("--hidden/--no-hidden", help="Include hidden files.")]


def _scan(
    root: Path,
    config: Path | None,
    min_size: int | None,
    max_size: int | None,
    exclude: list[str] | None,
    hidden: bool | None,
) -> ScanResult:
    try:
        options = load_options(config)
        options = replace(
            options,
            min_size=options.min_size if min_size is None else min_size,
            max_size=options.max_size if max_size is None else max_size,
            exclude=options.exclude + tuple(exclude or ()),
            hidden=options.hidden if hidden is None else hidden,
        )
        options = ScanOptions(**vars(options))
        with console.status("Scanning and hashing candidate files..."):
            return scan_directory(root, options)
    except (ConfigurationError, OSError, ValueError) as exc:
        error_console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=2) from exc


@app.command()
def scan(
    root: Root,
    config: Config = None,
    min_size: MinSize = None,
    max_size: MaxSize = None,
    exclude: Exclude = None,
    hidden: Hidden = None,
) -> None:
    """Scan and show a summary plus duplicate groups; never delete files."""
    show_result(console, _scan(root, config, min_size, max_size, exclude, hidden))


@app.command()
def duplicates(
    root: Root,
    config: Config = None,
    min_size: MinSize = None,
    max_size: MaxSize = None,
    exclude: Exclude = None,
    hidden: Hidden = None,
) -> None:
    """Show duplicate groups only."""
    show_result(console, _scan(root, config, min_size, max_size, exclude, hidden), groups_only=True)


@app.command()
def export(
    root: Root,
    output: Annotated[Path, typer.Option("--output", help="JSON output path.")],
    config: Config = None,
    min_size: MinSize = None,
    max_size: MaxSize = None,
    exclude: Exclude = None,
    hidden: Hidden = None,
) -> None:
    """Scan and export a reusable JSON report."""
    result = _scan(root, config, min_size, max_size, exclude, hidden)
    try:
        export_json(result, output)
    except OSError as exc:
        error_console.print(f"[red]Export failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    console.print(f"Exported {len(result.groups)} groups to {output}")


@app.command()
def delete(
    root: Root,
    config: Config = None,
    min_size: MinSize = None,
    max_size: MaxSize = None,
    exclude: Exclude = None,
    hidden: Hidden = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Preview removals only.")] = False,
    yes: Annotated[
        bool, typer.Option("--yes", help="Confirm all shown plans; keep first file.")
    ] = False,
    keep_index: Annotated[
        int | None, typer.Option("--keep-index", help="1-based keeper index for every group.")
    ] = None,
) -> None:
    """Show each group and remove verified copies after explicit confirmation."""
    result = _scan(root, config, min_size, max_size, exclude, hidden)
    for error in result.errors:
        error_console.print(f"[yellow]Warning:[/yellow] {error}")
    if not result.groups:
        console.print("No duplicate groups found.")
        return
    failures = 0
    for number, group in enumerate(result.groups, 1):
        show_groups(console, (group,))
        if keep_index is not None:
            selected = keep_index
        elif yes or dry_run:
            selected = 1
        else:
            selected = typer.prompt(f"Group {number}: number of file to keep", default=1, type=int)
        try:
            plan = make_plan(group, selected - 1)
        except ValueError as exc:
            error_console.print(f"[red]{exc}[/red]")
            raise typer.Exit(code=2) from exc
        console.print(f"KEEP: {plan.keep.path}")
        for file in plan.delete:
            console.print(f"{'WOULD DELETE' if dry_run else 'DELETE'}: {file.path}")
        if dry_run:
            continue
        if not yes and not typer.confirm(
            f"Delete the listed files in group {number}?", default=False
        ):
            console.print("Skipped group.")
            continue
        deleted, errors = execute_plan(plan)
        for path in deleted:
            console.print(f"Deleted: {path}")
        for error in errors:
            error_console.print(f"[red]Failed:[/red] {error}")
        failures += len(errors)
    if failures:
        raise typer.Exit(code=1)
