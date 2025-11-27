#!/usr/bin/env bash
set -euo pipefail

# IMPORTANT: This script has been updated to support --id and --file arguments
# for consistency with the new 'shai' unified CLI.

INPUT_ARG=""
ID_ARG=""
CONTEXT_FILE=""

# Parse arguments for flexible usage
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
# Default if no ID is provided (e.g., if run directly without 'shai' wrapper)
if [[ -n "$ID_ARG" ]]; then
  OUTPUT_DIR="output/essay-${ID_ARG}"
else
  OUTPUT_DIR="output/essay-$(date +%Y%m%d-%H%M%S)" # Fallback auto-ID
fi
mkdir -p "$OUTPUT_DIR"

# Helper: Mandatory output enforcement
require_file() {
  local filename="$1"
  if [[ ! -f "$filename" ]]; then
    echo "ERROR: Required output file '$filename' was NOT created."
    exit 1
  fi
}

# Determine the essay topic content
ESSAY_TOPIC_CONTENT=""
if [[ -n "$CONTEXT_FILE" ]]; then
  ESSAY_TOPIC_CONTENT=$(<"$CONTEXT_FILE") # Read file content
elif [[ -n "$INPUT_ARG" ]]; then
  ESSAY_TOPIC_CONTENT="$INPUT_ARG"
else
  echo "Error: No essay topic provided. Use 'shai essay \"Your topic\"' or 'shai essay --file topic.txt'."
  exit 1
fi

# Write the essay topic to a file for consistent file-based processing
TOPIC_FILE="$OUTPUT_DIR/essay_topic.txt"
echo "$ESSAY_TOPIC_CONTENT" > "$TOPIC_FILE"
echo "Essay topic saved to $TOPIC_FILE"

# Define files for agent stages, using the OUTPUT_DIR
PLAN_FILE="$OUTPUT_DIR/essay_plan.md"
ESSAY_DRAFT_FILE="$OUTPUT_DIR/essay_draft.md"
FINAL_ESSAY_FILE="$OUTPUT_DIR/essay_final.md"


echo "--- Running Essay Pipeline (ID: ${ID_ARG:-auto-generated}) ---"

# Stage 1: Planner Agent
read -r -d '' PLANNER_PROMPT <<EOF || true
You are the **ESSAY PLANNER**.

MANDATORY BEHAVIOR:
- You MUST read the user's essay topic from the file: \`${TOPIC_FILE}\`
- You MUST create a detailed plan for the essay, including structure, key arguments, and points to cover.
- You MUST write the plan to the file: \`${PLAN_FILE}\`
- The plan should be clear, concise, and structured with markdown headings.

TASK: Create an essay plan based on the topic in \`${TOPIC_FILE}\`.
EOF

echo "Running Planner Agent..."
opencode run "$PLANNER_PROMPT"
require_file "$PLAN_FILE"
echo "Planner completed. Plan saved to $PLAN_FILE"


# Stage 2: Writer Agent
read -r -d '' WRITER_PROMPT <<EOF || true
You are the **ESSAY WRITER**.

MANDATORY BEHAVIOR:
- You MUST read the essay plan from: \`${PLAN_FILE}\`
- You MUST write a comprehensive essay based on this plan.
- You MUST write the essay to the file: \`${ESSAY_DRAFT_FILE}\`
- The essay should be well-structured, coherent, and follow academic writing standards.
- DO NOT include an introduction like "Based on the plan..." just write the essay content.
- DO NOT include "Conclusion" or "References" unless specifically instructed in the plan.

TASK: Write the essay following the plan in \`${PLAN_FILE}\`.
EOF

echo "Running Writer Agent..."
opencode run "$WRITER_PROMPT"
require_file "$ESSAY_DRAFT_FILE"
echo "Writer completed. Draft saved to $ESSAY_DRAFT_FILE"


# Stage 3: Reviewer Agent
read -r -d '' REVIEWER_PROMPT <<EOF || true
You are the **ESSAY REVIEWER**.

MANDATORY BEHAVIOR:
- You MUST read the original essay plan from: \`${PLAN_FILE}\`
- You MUST read the essay draft from: \`${ESSAY_DRAFT_FILE}\`
- You MUST critically review the essay against the plan, checking for completeness, coherence, factual accuracy (if implied), grammar, and style.
- You MUST provide constructive feedback. If changes are needed, you MUST rewrite/refine the essay entirely, incorporating your suggestions.
- If the essay is already excellent and needs no changes, state that and output the original essay content as the final output.
- You MUST write the final, reviewed essay (or the original if no changes) to the file: \`${FINAL_ESSAY_FILE}\`

TASK: Review and refine the essay draft based on the plan.
EOF

echo "Running Reviewer Agent..."
opencode run "$REVIEWER_PROMPT"
require_file "$FINAL_ESSAY_FILE"
echo "Reviewer completed. Final essay saved to $FINAL_ESSAY_FILE"

echo "--- Essay Pipeline Finished ---"
echo "Final output is in: $FINAL_ESSAY_FILE"
```
