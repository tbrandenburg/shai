#!/usr/bin/env bash
set -euo pipefail

RFQ_FILE="${1:-}"

if [[ -z "$RFQ_FILE" ]]; then
  echo "Usage: $0 <path-to-rfq-file>"
  echo "Example: $0 input/rfq.md"
  exit 1
fi

if [[ ! -f "$RFQ_FILE" ]]; then
  echo "ERROR: RFQ file not found: $RFQ_FILE"
  exit 1
fi

# Read the RFQ file content
RFQ_DETAILS=$(cat "$RFQ_FILE")

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

pause_for_review() {
  echo ""
  read -p "Review the document. Press ENTER to continue or Ctrl+C to stop... " -r
  echo ""
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

INTAKE_PROMPT="You are the **RFQ Intake Agent** for the Possible RFQ & Project Assessment pipeline.

## MANDATORY RULES
- You **must not** perform any web searches.
- You **must not** remove information from the original request.
- You **must** parse the provided RFQ details into a structured brief that explicitly flags automation-ready opportunities.
- You **must** use MCP tools to write the structured document to ${INTAKE_OUTPUT}.
- You **must not** finish until ${INTAKE_OUTPUT} has been successfully created.

## RFQ

${RFQ_DETAILS}

## PRIMARY TASK
Analyze the RFQ and convert it into a structured intake document with a clear focus on automation opportunities.

Retain as much as information as possible given by the RFQ (lost items are lost valuable information!)
Focus on restructuring and clarity, instead of removing.

Place the full structured analysis in ${INTAKE_OUTPUT}.

## THE STRUCTURED INTAKE DOCUMENT MUST INCLUDE

### 1. AI Investment Context
Document the **initial AI setup investment** that enables this accelerated delivery

### 2. Basic RFQ Metadata
Extract and list:
- Client name  
- Project type  
- Scope  
- Input
- References (be very specific about any paths and examples provided)
- Deliverables  
- Budget range  
- Timeline expectations  
- Key constraints (technical, legal, organizational, etc.)

### 3. Acceptance Criteria

### 4. Open questions

### 5. Assumptions

### 6. Milestones
Derive milestones under consideration of given schedule constraints like demo dates.

### 7. Minimum Viable Product (MVP) Definition

### 8. Risks & Mitigations

"

opencode run "$INTAKE_PROMPT"

require_file "$INTAKE_OUTPUT"
echo "Intake Agent produced: ${INTAKE_OUTPUT}"
pause_for_review
echo ""

#############################################
# STAGE 2 — Technical Assessment Agent (agentic focus)
#############################################

echo "Running Technical Assessment Agent (AI-optimized)..."

TECHNICAL_PROMPT="You are the **Agent-Oriented Technical Assessment Agent** in the
Possible RFQ & Project Assessment pipeline.

## MANDATORY RULES

-   You **must** read the intake document from ${TECHNICAL_INPUT}.
-   You **must** read and deeply understand examples and references from ${TECHNICAL_INPUT}.
-   You **may** perform web searches to research latest technologies, state-of-the-art approaches, and current best practices.
-   You **must** write the technical assessment to ${TECHNICAL_OUTPUT}
    using MCP tools.
-   You **must not** finish the task until ${TECHNICAL_OUTPUT} is
    successfully created.

## PRIMARY TASK

Produce a technical architecture and delivery approach that **maximizes
the use of AI agents** while ensuring feasibility and quality.

Keep your chat response brief; place the full technical assessment in
${TECHNICAL_OUTPUT}.

## THE ASSESSMENT MUST INCLUDE

### 1. AI Infrastructure Investment Analysis

Explicitly document the **initial AI investment** that enables cost-effective delivery

### 2. Technical Architecture Overview

-   Systems, components, data flows, and key AI-enabled elements.

### 3. Delivery Approach

-   How the project will be executed to leverage AI agents effectively.

### 4. Component-Level Breakdown

For each project component, specify:
- Recommended **AI agents/tools/prompts**
- Required **human roles**
- Collaboration model: - **Autonomous** (AI-only) - **Human-in-the-loop** - **Human-only**

### 5. Resource Estimates

-   Hours and costs **separately** for:
    -   AI agent labor
    -   Human labor (incl. project work and initial agent setup)
-   Note any **platform/tooling costs**.

### 6. Technical Risks & Mitigations

-   Highlight risks, especially around **automation boundaries**.
-   Include recommended mitigations.
"

opencode run "$TECHNICAL_PROMPT"

require_file "$TECHNICAL_OUTPUT"
echo "Technical Assessment produced: ${TECHNICAL_OUTPUT}"
pause_for_review
echo ""

#############################################
# STAGE 3 — Quotation Generator Agent (agentic cost optimization)
#############################################

echo "Running Quotation Generator Agent (AI-optimized)..."

QUOTE_PROMPT="You are the **AI-Leveraged Quotation Generator Agent** within the
Possible RFQ & Project Assessment pipeline.

## MANDATORY RULES

-   You **must** read and use both prior inputs: ${QUOTE_INPUT_A} and
    ${QUOTE_INPUT_B}.
-   You **must not** perform any web searches.
-   You **must** write the final quotation to ${QUOTE_OUTPUT} using
    MCP tools.
-   You **must not** finish until ${QUOTE_OUTPUT} has been
    successfully created.

## PRIMARY TASK

Generate a concise, client-ready quotation optimized for **maximum AI
labor use** to reduce cost and timeline **without lowering quality**.

Write only a brief high-level summary in the chat response; place the
full detailed quotation in ${QUOTE_OUTPUT}.

## THE QUOTATION MUST INCLUDE

1.  **Executive Summary**
2.  **Scope of Work**
3.  **Assumptions**
4.  **Task clustering**
  * Create four clusters and assign all work packages to one of them:
    1.  **No AI** - fully human labor
    2.  **Full AI** - fully automated
    3.  **Hybrid** - AI-assisted human labor
    4.  **Likely AI** - AI bet; automation is probable but not guaranteed
  * **For each** cluster, include:
    * Total number of work packages
    * Costs and cost share of total project
    * Initial AI investment effort (if any)
    * Associated risks including their financial impact
    * Cost/time savings compared to human-only baseline considering the initial AI investments
    * Identification and justification of human-only tasks
5.  **Phased Delivery Plan**
6.  **Risk Disclosure & Mitigation Strategies**
7.  **Pricing Tables**
  - Overall comparison of **human-only** baseline costs vs. **AI optimized** costs and resulting **savings**
  - Clustered comparison of **human-only** baseline costs vs. **AI optimized** costs and resulting **savings**
  - Clustered **budget in risk**, **invest**, human/AI **hours**, human/AI **costs** and resulting **savings**
8.  **Summary**
  - Very brief summary with:
    - Total budget in risk
    - Total invest
    - Total costs
    - Total savings compared to human-only baseline (in currency and percentage)
9.  **Commercials & Terms**

## KNOWLEDGE BASE

- Students and developers both cost **\~90 €/hour**.
- AI agents cost **\~10 €/hour**.
"

opencode run "$QUOTE_PROMPT"

require_file "$QUOTE_OUTPUT"
echo "Quotation Generator produced: ${QUOTE_OUTPUT}"
pause_for_review
echo ""

#############################################
# STAGE 4 — Review & Quality Check Agent (agent framing)
#############################################

echo "Running Review & Quality Check Agent (AI-optimized)..."

FINAL_PROMPT="You are the **Review & Quality Check Agent** for the AI-optimized RFQ pipeline.

MANDATORY BEHAVIOR:
- You MUST read the draft quotation from: ${FINAL_INPUT}.
- You MUST NOT perform any web searches.
- You MUST use MCP tools to write the finalized quotation to: ${FINAL_OUTPUT}.
- You MUST NOT finish without creating ${FINAL_OUTPUT}.

TASK:
- Validate that AI vs human responsibilities are clearly delineated, financially sound, and persuasive.
- Ensure tone, formatting, and risk disclosures inspire confidence.
- Reinforce cost/time savings, note governance/oversight plans, and make the document client-ready.
- Keep your direct response minimal; the polished document goes into the output file."

opencode run "$FINAL_PROMPT"

require_file "$FINAL_OUTPUT"
echo "Review & Quality Check produced: ${FINAL_OUTPUT}"
echo ""

#############################################
# STAGE 5 — PDF Generation
#############################################

echo "Generating PDFs from markdown files..."

# Check if pandoc is available
if ! command -v pandoc &> /dev/null; then
  echo "WARNING: pandoc not found. Skipping PDF generation."
  echo "Install pandoc to enable PDF output: apt-get install pandoc texlive-xetex"
else
  PANDOC_OPTS="--pdf-engine=xelatex -V geometry:margin=0.75in -V mainfont=\"DejaVu Sans\" -V monofont=\"DejaVu Sans Mono\" -V fontsize=10pt -V linestretch=1.15 -V papersize=a4"
  
  # Generate PDFs for each markdown file
  for md_file in "$INTAKE_OUTPUT" "$TECHNICAL_OUTPUT" "$QUOTE_OUTPUT" "$FINAL_OUTPUT"; do
    if [[ -f "$md_file" ]]; then
      pdf_file="${md_file%.md}.pdf"
      echo "Converting $md_file to PDF..."
      if pandoc "$md_file" -o "$pdf_file" $PANDOC_OPTS 2>/dev/null; then
        echo "  ✓ Created: $pdf_file"
      else
        echo "  ✗ Failed to create PDF for $md_file"
      fi
    fi
  done
  
  echo ""
fi

#############################################
# DONE
#############################################

echo "AI-optimized RFQ pipeline finished successfully!"
echo "Generated files:"
echo "  $INTAKE_OUTPUT"
echo "  $TECHNICAL_OUTPUT"
echo "  $QUOTE_OUTPUT"
echo "  $FINAL_OUTPUT"

if command -v pandoc &> /dev/null; then
  echo ""
  echo "PDF files:"
  echo "  ${INTAKE_OUTPUT%.md}.pdf"
  echo "  ${TECHNICAL_OUTPUT%.md}.pdf"
  echo "  ${QUOTE_OUTPUT%.md}.pdf"
  echo "  ${FINAL_OUTPUT%.md}.pdf"
fi
