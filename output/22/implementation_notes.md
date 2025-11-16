# Implementation Notes for `roll-dice`

## Project Layout
- `pyproject.toml` — defines the project metadata, declares `roll-dice` in `[project.scripts]`, and uses Hatchling for builds.
- `src/roll_dice/__init__.py` — marks the package; intentionally empty.
- `src/roll_dice/cli.py` — exposes `main()` and the `roll_die()` helper that prints the dice result.
- `README.md` — short overview required by the `readme` field.

## Setup & Dependencies
1. Ensure the Astral `uv` tool is available (install with `python -m pip install uv` if needed).
2. From `output/22`, run `uv run roll-dice` (or `uv sync`) once; uv will provision `.venv` automatically based on `pyproject.toml`.
3. No third-party dependencies are required; the standard library `random` module powers the dice roll.

## Command Behavior
- The CLI entry point is `roll_dice.cli:main`, registered as `roll-dice`.
- `roll_die()` uses `random.SystemRandom().randint(1, 6)` to ensure inclusive bounds.
- `main()` prints the integer with the default newline and returns exit code 0; no other text is emitted.
- Incoming CLI arguments are ignored, so `uv run roll-dice anything` behaves the same as the base invocation.

## Running the Command
```bash
cd output/22
uv run roll-dice
```
- Each invocation yields exactly one integer between 1 and 6. Extra whitespace or adornments are never printed.
- Subsequent runs re-use the `.venv` provisioned on first execution.

## Maintenance Notes
- If uv emits a warning about `tool.uv.dev-dependencies`, it can be safely ignored for now because the project has no dev dependencies; upgrade to `dependency-groups` when practical.
- To make packaging deterministic in other environments, include this directory as-is and rely on `uv sync` for dependency locking.
