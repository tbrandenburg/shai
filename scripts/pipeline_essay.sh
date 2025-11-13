#!/usr/bin/env bash
set -euo pipefail

TOPIC="${1:-}"

if [[ -z "$TOPIC" ]]; then
  echo "Usage: $0 \"Essay topic\""
  exit 1
fi

#############################################
# CONFIGURATION — Input/Output per agent
#############################################

OUTPUT_DIR="output"
mkdir -p "$OUTPUT_DIR"

PLANNER_INPUT=""
PLANNER_OUTPUT="$OUTPUT_DIR/plan.md"

WRITER_INPUT="$PLANNER_OUTPUT"
WRITER_OUTPUT="$OUTPUT_DIR/essay.md"

REVIEWER_INPUT="$WRITER_OUTPUT"
REVIEWER_OUTPUT="$OUTPUT_DIR/review.md"


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
# STEP 1 — PLANNER (must use web search)
#############################################

echo "Running Planner..."

PLANNER_PROMPT="You are the **PLANNING STAGE** of a writing pipeline.

MANDATORY BEHAVIOR:
- You MUST perform a quick web search (keep them concise and targeted).
- You MUST cite sources and incorporate findings into your outline.
- You MUST use MCP tools to write the final outline to: \`${PLANNER_OUTPUT}\`
- TIMEOUT SAFETY: Keep your searches focused and avoid overly long operations.
- You MUST NOT finish without creating \`${PLANNER_OUTPUT}\`.

TASK:
- Create a hierarchical outline for: \"${TOPIC}\"
- Base it on your web research.
- Keep your text response brief.

Essay Topic: \"${TOPIC}\""

opencode run "$PLANNER_PROMPT"

require_file "$PLANNER_OUTPUT"
echo "Planner completed and produced: ${PLANNER_OUTPUT}"
echo ""


#############################################
# STEP 2 — WRITER (must use web search)
#############################################

echo "Running Writer..."

WRITER_PROMPT="You are the **WRITING STAGE** of a writing pipeline.

MANDATORY BEHAVIOR:
- You MUST read the outline from: \`${PLANNER_OUTPUT}\`
- You MUST perform targeted web searches for factual information and evidence.
- TIMEOUT SAFETY: Keep searches concise; focus on 2-3 key topics per search.
- You MUST use MCP tools to write the essay to: \`${WRITER_OUTPUT}\`
- You MUST NOT finish without creating \`${WRITER_OUTPUT}\`.

TASK:
- Write a detailed essay in Markdown based on the outline and research.
- Keep your text response brief."

opencode run "$WRITER_PROMPT"

require_file "$WRITER_OUTPUT"
echo "Writer completed and produced: ${WRITER_OUTPUT}"
echo ""


#############################################
# STEP 3 — REVIEWER (NO web search allowed)
#############################################

echo "Running Reviewer..."

REVIEWER_PROMPT="You are the **REVIEW STAGE** of a writing pipeline.

MANDATORY BEHAVIOR:
- You MUST read the essay from: \`${WRITER_OUTPUT}\`
- You MUST NOT perform any web searches.
- You MUST use MCP tools to write the revised essay to: \`${REVIEWER_OUTPUT}\`
- You MUST NOT finish without creating \`${REVIEWER_OUTPUT}\`.

TASK:
- Review the essay for structure, clarity, logic, and coherence.
- Revise and improve it.
- Keep your text response brief."

opencode run "$REVIEWER_PROMPT"

require_file "$REVIEWER_OUTPUT"
echo "Reviewer completed and produced: ${REVIEWER_OUTPUT}"
echo ""


#############################################
# DONE
#############################################

echo "Pipeline finished successfully!"
echo "Generated files:"
echo "  $PLANNER_OUTPUT"
echo "  $WRITER_OUTPUT"
echo "  $REVIEWER_OUTPUT"
