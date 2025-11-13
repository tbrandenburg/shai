#!/usr/bin/env bash
set -euo pipefail

RFQ_DETAILS="${1:-}"

if [[ -z "$RFQ_DETAILS" ]]; then
  echo "Usage: $0 \"RFQ details (client, scope, budget, timeline)\""
  exit 1
fi

#############################################
# CONFIGURATION — Input/Output per agent
#############################################

OUTPUT_DIR="output"
mkdir -p "$OUTPUT_DIR"

INTAKE_OUTPUT="$OUTPUT_DIR/rfq_intake_ai.md"

TECHNICAL_INPUT="$INTAKE_OUTPUT"
TECHNICAL_OUTPUT="$OUTPUT_DIR/technical_assessment_ai.md"

QUOTE_INPUT_A="$INTAKE_OUTPUT"
QUOTE_INPUT_B="$TECHNICAL_OUTPUT"
QUOTE_OUTPUT="$OUTPUT_DIR/quotation_ai.md"

FINAL_INPUT="$QUOTE_OUTPUT"
FINAL_OUTPUT="$OUTPUT_DIR/final_quotation_ai.md"

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
# Clean up previous outputs for this pipeline
#############################################

rm -f \
  "$INTAKE_OUTPUT" \
  "$TECHNICAL_OUTPUT" \
  "$QUOTE_OUTPUT" \
  "$FINAL_OUTPUT"

#############################################
# STAGE 1 — Intake Agent (automation-aware)
#############################################

echo "Running Intake Agent (AI-optimized)..."

INTAKE_PROMPT="You are the **Automation-Aware Intake Agent** for the Possible RFQ & Project Assessment pipeline.

MANDATORY BEHAVIOR:
- You MUST NOT perform any web searches.
- You MUST parse the provided RFQ details into a structured brief that explicitly flags automation-ready opportunities.
- You MUST use MCP tools to write the structured document to: \`${INTAKE_OUTPUT}\`
- You MUST NOT finish without creating \`${INTAKE_OUTPUT}\`.

TASK:
- Analyze the following RFQ submission: \"${RFQ_DETAILS}\"
- Extract and list: client name, project type, scope, deliverables, budget range, timeline expectations, and constraints.
- For each deliverable or workflow, classify whether an AI agent can own it end-to-end, support a human in the loop, or requires human-only execution. Provide reasoning plus assumptions.
- Highlight quick wins where autonomous agents can reduce cost or turnaround time.
- Keep this console response brief; the full structured analysis belongs in the output file."

opencode run "$INTAKE_PROMPT"

require_file "$INTAKE_OUTPUT"
echo "Intake Agent produced: ${INTAKE_OUTPUT}"
echo ""

#############################################
# STAGE 2 — Technical Assessment Agent (agentic focus)
#############################################

echo "Running Technical Assessment Agent (AI-optimized)..."

TECHNICAL_PROMPT="You are the **Agent-Oriented Technical Assessment Agent** of the Possible RFQ & Project Assessment pipeline.

MANDATORY BEHAVIOR:
- You MUST read the intake document from: \`${TECHNICAL_INPUT}\`.
- You MUST NOT perform any web searches.
- You MUST use MCP tools to write the technical assessment to: \`${TECHNICAL_OUTPUT}\`.
- You MUST NOT finish without creating \`${TECHNICAL_OUTPUT}\`.

TASK:
- Define the technical architecture and delivery approach while maximizing AI agent participation.
- For each project component, specify the recommended AI agents/tools, human roles, and collaboration model (autonomous, human-in-the-loop, or human-only).
- Estimate resource requirements with separate hour/cost projections for agent labor vs human labor, noting any platform/tooling costs.
- Identify technical risks, especially around automation boundaries, plus mitigations.
- Keep this response brief; provide the detailed assessment in the output file."

opencode run "$TECHNICAL_PROMPT"

require_file "$TECHNICAL_OUTPUT"
echo "Technical Assessment produced: ${TECHNICAL_OUTPUT}"
echo ""

#############################################
# STAGE 3 — Quotation Generator Agent (agentic cost optimization)
#############################################

echo "Running Quotation Generator Agent (AI-optimized)..."

QUOTE_PROMPT="You are the **AI-Leveraged Quotation Generator Agent** of the Possible RFQ & Project Assessment pipeline.

MANDATORY BEHAVIOR:
- You MUST read prior outputs: \`${QUOTE_INPUT_A}\` and \`${QUOTE_INPUT_B}\`.
- You MUST NOT perform any web searches.
- You MUST use MCP tools to write the quotation to: \`${QUOTE_OUTPUT}\`.
- You MUST NOT finish without creating \`${QUOTE_OUTPUT}\`.

TASK:
- Produce a client-ready quotation that maximizes AI agent labor to reduce cost and timeline while maintaining quality.
- Include: executive summary, scope, phased plan, and a pricing table broken into Agentic Work vs Human Work (showing hours, rates, and total cost savings).
- Highlight tasks that remain human-only and justify why automation is unsafe or infeasible.
- Quantify estimated savings in money and time relative to a traditional human-only approach.
- Keep this reply short; place the detailed quotation in the output file."

opencode run "$QUOTE_PROMPT"

require_file "$QUOTE_OUTPUT"
echo "Quotation Generator produced: ${QUOTE_OUTPUT}"
echo ""

#############################################
# STAGE 4 — Review & Quality Check Agent (agent framing)
#############################################

echo "Running Review & Quality Check Agent (AI-optimized)..."

FINAL_PROMPT="You are the **Review & Quality Check Agent** for the AI-optimized RFQ pipeline.

MANDATORY BEHAVIOR:
- You MUST read the draft quotation from: \`${FINAL_INPUT}\`.
- You MUST NOT perform any web searches.
- You MUST use MCP tools to write the finalized quotation to: \`${FINAL_OUTPUT}\`.
- You MUST NOT finish without creating \`${FINAL_OUTPUT}\`.

TASK:
- Validate that AI vs human responsibilities are clearly delineated, financially sound, and persuasive.
- Ensure tone, formatting, and risk disclosures inspire confidence in the automation strategy.
- Reinforce cost/time savings, note governance/oversight plans, and make the document client-ready.
- Keep your direct response minimal; the polished document goes into the output file."

opencode run "$FINAL_PROMPT"

require_file "$FINAL_OUTPUT"
echo "Review & Quality Check produced: ${FINAL_OUTPUT}"
echo ""

#############################################
# DONE
#############################################

echo "AI-optimized RFQ pipeline finished successfully!"
echo "Generated files:"
echo "  $INTAKE_OUTPUT"
echo "  $TECHNICAL_OUTPUT"
echo "  $QUOTE_OUTPUT"
echo "  $FINAL_OUTPUT"
