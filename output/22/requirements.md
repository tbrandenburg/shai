# Roll Dice Requirements

## Functionality
- Provide a Python-based command named `roll-dice` that produces a pseudo-random integer each time it is invoked.
- The integer must be between 1 and 6 inclusive; each valid face value should be possible on every run.
- Exactly one numeric value is emitted per execution with no descriptive text, prompts, or additional formatting other than the trailing newline from stdout.

## Interface
- Primary invocation: `uv run roll-dice` from the project root using uv for dependency and script management.
- The command takes no positional or optional arguments and should ignore unexpected inputs rather than prompting.
- Output is emitted to standard output so that the command can be piped or captured by other tooling if desired.

## Constraints & Assumptions
- Project must be fully managed via uv, including a reproducible `pyproject.toml` that registers the `roll-dice` script entry point.
- Implementation should rely only on Python's standard library to keep the project lightweight; no external packages are expected.
- Randomness source can be the default PRNG (`random.randint`), assuming its distribution is sufficient for casual dice rolling.
- Error handling should fail fast with non-zero exit codes if the runtime environment cannot produce a number, but the happy path must never log extra chatter.
