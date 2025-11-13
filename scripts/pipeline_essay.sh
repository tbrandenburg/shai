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

PLANNER_INPUT=""
PLANNER_OUTPUT="plan.md"

WRITER_INPUT="$PLANNER_OUTPUT"
WRITER_OUTPUT="essay.md"

REVIEWER_INPUT="$WRITER_OUTPUT"
REVIEWER_OUTPUT="review.md"


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

PLANNER_PROMPT=$(cat <<EOF
You are the **PLANNING STAGE** of a writing pipeline.

MANDATORY BEHAVIOR:
- You MUST perform multiple web searches to explore:
  • background information on the topic
  • related subtopics
  • debates or controversies
  • historical context
- You MUST cite what you find and incorporate it into your outline.
- You MUST use MCP tools to write the final outline to the file: ${PLANNER_OUTPUT}
- You MUST NOT finish your task without creating \`${PLANNER_OUTPUT}\`.

TASK:
- Create a deeply informed, hierarchical outline for the topic based on your web research.
- Your text response should only be a short summary of what you created.

Essay Topic: "${TOPIC}"
EOF
)

opencode run \
  --prompt "$PLANNER_PROMPT"

require_file "$PLANNER_OUTPUT"
echo "Planner completed and produced: ${PLANNER_OUTPUT}"
echo ""


#############################################
# STEP 2 — WRITER (must use web search)
#############################################

echo "Running Writer..."

WRITER_PROMPT=$(cat <<EOF
You are the **WRITING STAGE** of a writing pipeline.

MANDATORY BEHAVIOR:
- You MUST read the outline from the file: ${WRITER_INPUT}
- You MUST perform multiple web searches to obtain:
  • factual information
  • contemporary debates
  • supporting evidence and arguments
  • counterarguments
- You MUST integrate your findings into the essay.
- You MUST use MCP tools to write the complete essay to: ${WRITER_OUTPUT}
- You MUST NOT complete your task without creating \`${WRITER_OUTPUT}\`.

TASK:
- Write a detailed, well-structured essay in Markdown based on the outline and your research.
- Your text response should only summarize the essay you created.
EOF
)

opencode run \
  --file "$WRITER_INPUT" \
  --prompt "$WRITER_PROMPT"

require_file "$WRITER_OUTPUT"
echo "Writer completed and produced: ${WRITER_OUTPUT}"
echo ""


#############################################
# STEP 3 — REVIEWER (NO web search allowed)
#############################################

echo "Running Reviewer..."

REVIEWER_PROMPT=$(cat <<EOF
You are the **REVIEW STAGE** of a writing pipeline.

MANDATORY BEHAVIOR:
- You MUST read the essay from the file: ${REVIEWER_INPUT}
- You MUST NOT perform any web searches.
  (Your review must rely solely on the provided essay.)
- You MUST use MCP tools to write the revised essay to: ${REVIEWER_OUTPUT}
- You MUST NOT complete your task without creating \`${REVIEWER_OUTPUT}\`.

TASK:
- Review the essay for structure, clarity, logic, factual coherence, and argumentative quality.
- Revise and improve it.
- Your text response should only summarize the improvements you made.
EOF
)

opencode run \
  --file "$REVIEWER_INPUT" \
  --prompt "$REVIEWER_PROMPT"

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
