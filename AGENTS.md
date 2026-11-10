# Repository Guidelines

## Project Structure & Module Organization

This is a flat, Linux-focused Python 3 project for SmartGit 26.1:

- `smartgit_private_id.py` installs and checks a Bubblewrap launcher with a stable application-specific machine ID, and restores desktop entries on uninstall.
- `smartgit_evaluation.py` requests official evaluation credentials and verifies signatures, machine binding, and expiry.
- `test_smartgit_private_id.py` contains installer regression tests.
- `README.md` documents usage in Chinese; `package.json` provides optional Bun shortcuts.

There are no separate source, asset, or build-output directories. Keep related modules and tests at the repository root.

## Build, Test, and Development Commands

No build step or Python package installation is required; both tools use the standard library.

- `python3 -m unittest discover -v`: run the complete test suite.
- `bun run test`: optional equivalent; no `bun install` needed.
- `python3 smartgit_private_id.py --help`: inspect launcher commands.
- `python3 smartgit_evaluation.py --help`: inspect credential commands.
- `python3 smartgit_private_id.py check`: verify mappings after installation without launching SmartGit.

Manual launcher installation requires Bash, `bwrap`, namespace support, and SmartGit under `/usr/share/smartgit`. Installation modifies user configuration; use temporary paths and mocks for automated checks.

## Coding Style & Naming Conventions

Follow existing Python style: four-space indentation, `snake_case` functions and variables, `UPPER_SNAKE_CASE` constants, and descriptive names. Use `pathlib.Path` for filesystem operations and `argparse` for CLI interfaces. Keep dependencies within the standard library. No formatter or linter is configured.

## Testing Guidelines

Use `unittest`, `unittest.mock`, and `tempfile.TemporaryDirectory`. Name test files `test_*.py` and methods `test_*`. Cover successful operations, invalid inputs, reinstall stability, permissions, and failure paths that must preserve existing files. Tests should run offline without launching SmartGit or changing real user configuration. No coverage threshold is configured.

## Commit & Pull Request Guidelines

Git history is unavailable in this checkout, so no established commit convention can be confirmed. Use concise, imperative subjects, such as `Preserve desktop backup during reinstall`. Keep changes focused. PR descriptions should explain behavior changes, list validation commands and results, and link relevant issues. Update `README.md` when commands or supported behavior change.

## Security & Configuration

Preserve restrictive permissions for IDs and credentials (`0600`). Never commit credentials or machine identifiers. Preserve refusal to overwrite existing evaluation files and keep signature and binding checks intact. The launcher remaps ID files; it is not a complete privacy sandbox.
