#!/usr/bin/env bash
set -euo pipefail

INPUT_ARG="${1:-}"

show_usage() {
  cat <<'USAGE'
Usage: pipeline_task_machine.sh "High level task description"
   or: pipeline_task_machine.sh --file path/to/request.md
USAGE
}

if [[ -z "$INPUT_ARG" ]]; then
  show_usage
  exit 1
fi

if [[ "$INPUT_ARG" == "--file" ]]; then
  CONTEXT_FILE="${2:-}"
  if [[ -z "$CONTEXT_FILE" ]]; then
    echo "ERROR: Missing file path after --file."
    show_usage
    exit 1
  fi
  if [[ ! -f "$CONTEXT_FILE" ]]; then
    echo "ERROR: Task context file '$CONTEXT_FILE' not found."
    exit 1
  fi
  TASK_CONTEXT="$(cat "$CONTEXT_FILE")"
else
  if [[ -f "$INPUT_ARG" ]]; then
    TASK_CONTEXT="$(cat "$INPUT_ARG")"
  else
    TASK_CONTEXT="$INPUT_ARG"
  fi
fi

if [[ -z "$TASK_CONTEXT" ]]; then
  echo "ERROR: Task context is empty. Provide text or a file with content."
  exit 1
fi

#############################################
# CONFIGURATION
#############################################

OUTPUT_DIR="output"
mkdir -p "$OUTPUT_DIR"

PLAN_FILE="$OUTPUT_DIR/task_machine_plan.md"
TEMPLATE_FILE="templates/task_machine_multirole.md"

if [[ ! -f "$TEMPLATE_FILE" ]]; then
  echo "ERROR: Required task template '$TEMPLATE_FILE' not found."
  exit 1
fi

PLANNER_TEMPLATE_CONTENT="$(cat "$TEMPLATE_FILE")"

#############################################
# Helper: Mandatory output enforcement
#############################################

require_file() {
  local filename="$1"
  if [[ ! -f "$filename" ]]; then
    echo "ERROR: Required output file '$filename' was NOT created."
    exit 1
  fi
}

#############################################
# Clean up previous outputs
#############################################

rm -f "$PLAN_FILE"

#############################################
# STEP 1 — PLANNER
#############################################

echo "Running Task Machine Planner..."

PLANNER_PROMPT="You are the **TASK MACHINE PLANNER** in a two-stage pipeline.\n\nMANDATORY BEHAVIOR:\n- Read the user's high-level goal and constraints.\n- Produce a markdown document written to: \`${PLAN_FILE}\`.\n- The document MUST contain two sections: \n  1. \`## Context\` summarizing the overall objective.\n  2. \`## Chronologic Task List\` describing step-by-step tasks.\n- Every task MUST be self-contained, independent, and formatted as a markdown checkbox line in chronological order, e.g. \`- [ ] Task name — clear, actionable instructions...\`.\n- Include all details needed to execute each task without referencing other tasks.\n- Do NOT mark any task as completed.\n- You MUST use MCP tools to write the document and MUST NOT finish without creating \`${PLAN_FILE}\`.\n- You MUST incorporate the provided task template verbatim and ensure each listed role requirement is addressed.\n\nTASK TEMPLATE:\n${PLANNER_TEMPLATE_CONTENT}\n\nTASK:\nCreate the plan for the following goal:\n\n${TASK_CONTEXT}"

opencode run "$PLANNER_PROMPT"

require_file "$PLAN_FILE"
echo "Planner completed: ${PLAN_FILE}"
echo ""

#############################################
# STEP 2 — EXECUTOR LOOP
#############################################

echo "Entering executor loop..."
iteration=1
while grep -q "\\[ \\]" "$PLAN_FILE"; do
  echo "Running executor iteration ${iteration}..."
  EXECUTOR_PROMPT="You are the **TASK MACHINE EXECUTOR**.\n\nMANDATORY BEHAVIOR:\n- Read the shared plan at \`${PLAN_FILE}\`.\n- Identify the FIRST unchecked task (first line containing \`- [ ]\`).\n- Execute ONLY that task. Do not attempt subsequent tasks.\n- After completing the task, update the same line to \`- [x]\` and append a concise summary of what you accomplished, including any outputs or follow-up notes.\n- Do NOT alter other tasks except to add a short inline status note if strictly required by the executed task.\n- Use MCP tools to rewrite the updated plan back to \`${PLAN_FILE}\`.\n- You MUST NOT finish without updating \`${PLAN_FILE}\`.\n- If execution reveals new subtasks, append them as new unchecked tasks immediately after the current line.\n- Keep your console response brief; the authoritative record is the plan file.\n\nTASK:\nComplete only the first open task in the plan."

  opencode run "$EXECUTOR_PROMPT"

  require_file "$PLAN_FILE"
  echo "Executor iteration ${iteration} finished."
  echo ""
  iteration=$((iteration + 1))
done

echo "All tasks completed!"
echo "Final plan: ${PLAN_FILE}"
