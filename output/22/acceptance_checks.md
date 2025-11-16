# Acceptance Checks for `roll-dice`

## Prerequisites
- Ensure `uv` is installed and the project dependencies have been resolved (e.g., run `uv sync` if needed).
- All commands below are executed from the project root.

## Invocation & Exit Status
1. Run `uv run roll-dice`.
   - Expect a zero exit status.
   - Expect exactly one line of output before the process terminates.
2. Run `uv run roll-dice argument-that-should-be-ignored`.
   - Expect the same behavior as above: zero exit status and a single line response with no prompts or error chatter.

## Output Format & Range
3. Capture the output of `uv run roll-dice` (e.g., `output=$(uv run roll-dice)`).
   - Assert the output contains only digits with an optional trailing newline (regex `^[1-6]$`).
4. Repeat the command at least 10 times (manual loop or script).
   - Confirm each value is within 1–6.
   - Verify no additional characters, spaces, or labels accompany the integer on any run.

## Randomness Spot-Check
5. Over 10+ invocations, ensure that at least two distinct face values are observed; if not, rerun until diversity appears, noting any persistent bias for follow-up.

## Failure Handling
6. Introduce a simulated failure scenario (e.g., corrupting the module temporarily or running with insufficient permissions) only if practical.
   - Confirm the command exits non-zero and does not emit extra descriptive text on failure paths.

Document the observed outputs and any deviations in `output/22/test_report.md` during QA.
