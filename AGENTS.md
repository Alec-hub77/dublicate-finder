# AGENTS.md

## Project

Duplicate Finder is a Windows-friendly command-line application for finding duplicate files.

The application must scan directories recursively, identify duplicate files efficiently, display useful results in the terminal, and provide safe options for exporting and deleting duplicates.

## Technology

Use:

- Python 3.13+
- Typer for CLI
- Rich for terminal output
- pathlib for filesystem operations
- hashlib for hashing
- pytest for tests
- Ruff for linting and formatting
- mypy for static type checking

Prefer Python standard library functionality whenever possible.

Do not introduce additional dependencies unless there is a clear technical reason.

## Architecture

Keep responsibilities separated:

- `cli.py` — CLI commands and user interaction
- `scanner.py` — filesystem traversal and file discovery
- `hasher.py` — file hashing
- `models.py` — typed domain models
- `grouping.py` — duplicate detection and grouping
- `formatter.py` — terminal and export formatting
- `config.py` — configuration
- `exceptions.py` — application-specific exceptions

Business logic must not depend directly on Typer or Rich.

The core duplicate detection functionality should be usable independently from the CLI.

## Duplicate detection

A file is considered a duplicate only when:

1. The files have the same size.
2. Their complete SHA-256 hashes are identical.

Do not compare filenames when determining duplicates.

Do not read the entire contents of files into memory.

Hash files in chunks.

For very large files, avoid unnecessary work.

## Performance

Use a staged approach:

1. Discover files.
2. Group candidate files by file size.
3. Ignore sizes that occur only once.
4. Hash only candidate files.
5. Group files by SHA-256.

Use concurrency where it provides a measurable benefit, especially for hashing multiple files.

Do not create unbounded threads or processes.

## Safety

File deletion must be conservative.

The application must never delete files automatically during a normal scan.

Deletion must require explicit user intent.

Provide a dry-run mode.

Before deleting files, show exactly which files will be deleted.

Never delete all copies of a duplicate group. At least one copy must remain.

Do not follow directory symlinks by default.

Handle inaccessible files gracefully.

## Error handling

A single inaccessible, deleted, locked, or unreadable file must not terminate the entire scan.

Report errors to the user and continue processing other files.

Avoid broad `except Exception` unless there is a specific reason and the exception is logged or reported appropriately.

## CLI

The CLI should provide:

- `scan`
- `duplicates`
- `delete`
- `export`

Commands must have useful `--help` output.

Use meaningful exit codes.

Paths must work correctly on Windows.

## Testing

Write unit tests for core functionality.

Tests must cover:

- empty directories
- one file
- multiple unique files
- duplicate files
- files with the same name but different contents
- files with different sizes
- inaccessible files
- nested directories
- empty files
- deletion safety
- dry-run behavior
- CLI behavior

Use pytest fixtures and temporary directories.

Do not make tests depend on the user's real filesystem.

## Code quality

Use type hints throughout the application.

Keep functions reasonably small and focused.

Prefer immutable/read-only data structures where appropriate.

Avoid global mutable state.

Document non-obvious design decisions.

Do not over-engineer the application.

Before considering the implementation complete:

1. Run tests.
2. Run Ruff.
3. Run mypy.
4. Fix all errors.
5. Update README.md with actual usage examples.