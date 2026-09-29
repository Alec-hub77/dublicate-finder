# Duplicate Finder

A Windows-friendly Python CLI that finds duplicate files recursively using file size and complete SHA-256 hashes. Scanning never deletes files.

## Requirements and installation

Python 3.13 or newer. From PowerShell in this project directory:

```powershell
py -m venv .venv
.venv\Scripts\python -m pip install -e .
.venv\Scripts\duplicate-finder --help
```

If PowerShell cannot find `duplicate-finder`, use the module entry point, which does not require the Scripts directory on `PATH`:

```powershell
py -m duplicate_finder scan "D:\test\_dublicate"
```

With a project virtual environment, use `.venv\Scripts\python -m duplicate_finder scan "D:\test\_dublicate"`. Do not append a backslash after the closing quote in PowerShell.

For development, install `-e ".[dev]"` instead.

## Commands

```powershell
duplicate-finder scan "C:\Users\Alec\Downloads"
duplicate-finder duplicates "C:\Users\Alec\Downloads" --min-size 1024 --exclude "*.tmp" --hidden
duplicate-finder export "C:\Users\Alec\Downloads" --output duplicates.json
duplicate-finder delete "C:\Users\Alec\Downloads" --dry-run
duplicate-finder delete "C:\Users\Alec\Downloads"
duplicate-finder delete "C:\Users\Alec\Downloads" --yes
```

`--min-size` and `--max-size` use bytes and include the boundary. Repeat `--exclude` for multiple glob patterns. Hidden files and folders are skipped by default; `--hidden` includes them. All scan commands accept `--config config.toml`. Command-line values override configuration; excludes are added to configured patterns. Use `--help` on any command for its options.

`scan` shows counts and duplicate groups. `duplicates` shows groups only. `export` saves the full report, including timestamp, file paths, sizes, hashes, totals, and read errors. The JSON can be read without scanning again. `delete` displays each group, asks which numbered copy to keep, lists every proposed removal, then requests confirmation for that group. `--keep-index N` chooses the same numbered keeper in all groups. `--yes` confirms the displayed plans non-interactively and keeps the first copy by default. `--dry-run` only previews; it never prompts or removes anything.

Exit status is 0 for success, 1 for a deletion or export failure, and 2 for invalid paths, options, or configuration. Files that cannot be read are reported as warnings and scanning continues.

## How detection works

The scanner discovers regular files recursively, groups them by size, and hashes only files whose size occurs more than once. It reads each candidate in 1 MiB chunks and groups files by both size and full SHA-256 digest. Hashing uses a bounded thread pool (at most eight workers by default), useful when files reside on different disks or storage with overlapping I/O latency. Discovery is deterministic and deletion plans sort paths for a stable first choice.

## Safety and limitations

Directory and file symlinks are skipped. Before each deletion, the keeper and target are rechecked against their original size, modification time, and hash. If the keeper changes or becomes unreadable, the rest of that group is skipped. This protects against routine changes between scan and deletion, but concurrent writes or filesystem replacement in the tiny interval after verification remain possible; run deletion on a quiescent directory and review its plan. The scanner holds metadata for all discovered files and submits candidate hash jobs in one batch, so very large trees can use substantial memory. SHA-256 equality is treated as equivalence; byte-for-byte comparison is not performed. Empty files are valid duplicates, with zero potential savings.

## Configuration

Copy [examples/config.example.toml](examples/config.example.toml) and edit its commented settings. Configuration is optional.

## Development checks

```powershell
py -m pytest
py -m ruff check .
py -m ruff format --check .
py -m mypy
```

Possible improvements include bounded hash-job queues for very large scans, progress counts during each stage, and platform-specific file locking for stronger deletion guarantees.
