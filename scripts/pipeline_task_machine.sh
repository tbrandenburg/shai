#!/usr/bin/env bash
set -euo pipefail

INPUT_ARG=""
ID_ARG=""
CONTEXT_FILE=""

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --id)
      ID_ARG="$2"
      shift 2
      ;;
    --file)
      CONTEXT_FILE="$2"
      shift 2
      ;;
    *)
      if [[ -z "$INPUT_ARG" ]]; then
        INPUT_ARG="$1"
      fi
      shift
      ;;
  esac
done

# Set output directory with optional ID suffix
if [[ -n "$ID_ARG" ]]; then
  OUTPUT_DIR="output/${ID_ARG}"
else
  OUTPUT_DIR="output"
fi
mkdir -p "$OUTPUT_DIR"

show_usage() {
  cat <<'USAGE'
Usage: pipeline_task_machine.sh "High level task description" [--id <identifier>]
   or: pipeline_task_machine.sh --file path/to/request.md [--id <identifier>]

Options:
  --id <identifier>  Append identifier to output directory (output/<id>)
  --file <path>      Read task description from file
USAGE
}

if [[ -z "$INPUT_ARG" && -z "$CONTEXT_FILE" ]]; then
  show_usage
  exit 1
fi

# Handle context file based on input type
if [[ -n "$CONTEXT_FILE" ]]; then
  # Using --file argument
  if [[ ! -f "$CONTEXT_FILE" ]]; then
    echo "ERROR: Task context file '$CONTEXT_FILE' not found."
    exit 1
  fi
else
  # Using direct task description or filename
  if [[ -z "$INPUT_ARG" ]]; then
    echo "ERROR: No task description provided."
    show_usage
    exit 1
  fi
  
  if [[ -f "$INPUT_ARG" ]]; then
    CONTEXT_FILE="$INPUT_ARG"
  else
    CONTEXT_FILE="$OUTPUT_DIR/task_request.txt"
    printf "%s\n" "$INPUT_ARG" > "$CONTEXT_FILE"
  fi
fi

if [[ ! -f "$CONTEXT_FILE" ]]; then
  echo "ERROR: Unable to determine task context file."
  exit 1
fi

if [[ ! -s "$CONTEXT_FILE" ]]; then
  echo "ERROR: Task context is empty. Provide text or a file with content."
  exit 1
fi

#############################################
# CONFIGURATION
#############################################

PLAN_FILE="$OUTPUT_DIR/task_machine_plan.md"
TEMPLATE_FILE="templates/task_machine_multirole.md"
AGENTS_DIR=".github/agents"

if [[ ! -f "$TEMPLATE_FILE" ]]; then
  echo "ERROR: Required task template '$TEMPLATE_FILE' not found."
  exit 1
fi

if [[ ! -d "$AGENTS_DIR" ]]; then
  echo "ERROR: Required agents directory '$AGENTS_DIR' not found."
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

read -r -d '' PLANNER_PROMPT <<EOF || true
You are the **TASK MACHINE PLANNER** in a two-stage pipeline.

MANDATORY BEHAVIOR:
- Before planning, scan the output directory at \`${OUTPUT_DIR}\` for any previously created artifacts so your plan builds on the latest work.
- Use MCP tools to read both the user's high-level goal from \`${CONTEXT_FILE}\` and the multi-role task template stored at \`${TEMPLATE_FILE}\`.
- RECURSIVELY explore the \`${AGENTS_DIR}\` folder structure to understand all available agent roles and their capabilities. Read agent definition files to understand their purpose, focus areas, and working styles.
- Study the template's task patterns: how roles collaborate, file dependencies between tasks, and the structured workflow approach.
- For each role needed:
  * FIRST attempt to find a suitable existing agent in \`${AGENTS_DIR}\` that matches the required expertise
  * If a good match exists, use ONLY the agent name and include its file path (e.g., \`Agent Path: ${AGENTS_DIR}/05-data-ai/data-analyst.md\`) - do NOT redefine Purpose, Focus, or Style as these are already in the agent file
  * If NO suitable agent exists, create a custom role definition inline with Purpose, Focus, and Style (add \`Note: Custom role defined inline\`)
- Adapt the template's proven patterns to the user's request: use similar role collaboration, file handoffs, and task sequencing where applicable.
- NEVER copy or quote any portion of the template verbatim in the plan. Summaries must be rephrased in your own words.
- Produce a markdown document written to: \`${PLAN_FILE}\` with three sections: 
  1. \`## Context\` summarizing the overall objective.
  2. \`## Role Descriptions\` listing each role (with "Agent Path" if using GitHub agent, or custom definition if not).
  3. \`## Chronologic Task List\` describing step-by-step tasks that follow the template's collaboration patterns.
- Every task MUST be self-contained, independent, and formatted as: \`- [ ] [role-name] Task name — clear, actionable instructions...\`
- When adapting template tasks, maintain the file creation and reading patterns that enable role collaboration.
- Include all details needed to execute each task without referencing other tasks.
- Do NOT mark any task as completed.
- Only adopt the roles and deliverables that are genuinely relevant to the user's request; omit or simplify anything that would be unnecessary busywork.
- Keep the plan as lightweight as possible. If the user only wants a simple answer (e.g., a quick weather report), limit the plan to the fewest steps needed to fulfill that request rather than inventing elaborate multi-role workflows.
- This workflow is UNSUPERVISED: do not ask questions or seek confirmation—make decisions yourself based solely on the provided task description and files.

TASK:
Create the plan for the request described in the context file stored at \`${CONTEXT_FILE}\`.

EOF

opencode run "$PLANNER_PROMPT"

require_file "$PLAN_FILE"
echo "Planner completed: ${PLAN_FILE}"
echo "\n===== Task Plan ====="
cat "$PLAN_FILE"
echo "===== End Task Plan =====\n"
echo ""

#############################################
# STEP 2 — EXECUTOR LOOP
#############################################

echo "Entering executor loop..."
iteration=1
while grep -q "\\[ \\]" "$PLAN_FILE"; do
  # Count checkboxes for progress tracking
  total_tasks=$(grep -c "^- \[.\]" "$PLAN_FILE" || echo "0")
  completed_tasks=$(grep -c "^- \[x\]" "$PLAN_FILE" || echo "0")
  remaining_tasks=$(grep -c "^- \[ \]" "$PLAN_FILE" || echo "0")
  
  echo "Running executor iteration ${iteration}... (${completed_tasks}/${total_tasks} completed, ${remaining_tasks} remaining)"
  read -r -d '' EXECUTOR_PROMPT <<EOF || true
You are the **TASK MACHINE EXECUTOR**.

MANDATORY BEHAVIOR:
- Use MCP tools to read the shared plan at \`${PLAN_FILE}\`.
- Review the Context section to understand the overall objective.
- Set your working directory to \`${OUTPUT_DIR}\` for all file operations.
- Identify the FIRST unchecked task (first line containing \`- [ ]\`) and execute ONLY that task.
- BEFORE executing the task:
  1. Extract the role name from the task (e.g., [data-analyst], [Custom Marketing Specialist])
  2. Look up the role in the Role Descriptions section
  3. If the role has an "Agent Path", read the complete agent definition file using MCP tools and adopt that agent's full expertise
  4. If the role does not have an "Agent Path" use the Purpose, Focus, and Style from the plan's role description
  5. Fully embody that role's expertise, focus areas, working style, and domain knowledge
- Approach the task from that specific role's perspective, using their specialized skills and methodology.
- After completing the task, update the same line to \`- [x]\` and add a summary as an indented sub-point using \`* Summary: ...\` format on the next line.
- Do NOT alter other tasks except to add a short inline status note if strictly required by the executed task.
- If execution reveals new subtasks, append them as new unchecked tasks immediately after the current line.
- Use MCP tools to rewrite the updated plan back to \`${PLAN_FILE}\` before finishing.
- Keep your console response brief; the authoritative record is the plan file.
- This workflow is UNSUPERVISED: do not ask questions or seek confirmation—make decisions yourself based solely on the provided task description and files.
- Whenever you need up-to-date, version-specific library documentation or code examples, query the **context7 MCP server** to gather that information before proceeding.

TASK:
Complete only the first open task in the plan.
EOF

  opencode run "$EXECUTOR_PROMPT"

  require_file "$PLAN_FILE"
  echo "Executor iteration ${iteration} finished."
  echo ""
  iteration=$((iteration + 1))
done

# Final progress summary
final_total_tasks=$(grep -c "^- \[.\]" "$PLAN_FILE" || echo "0")
final_completed_tasks=$(grep -c "^- \[x\]" "$PLAN_FILE" || echo "0")

echo "All tasks completed! (${final_completed_tasks}/${final_total_tasks} tasks finished)"
echo "Final plan: ${PLAN_FILE}"
