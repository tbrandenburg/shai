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

INTAKE_OUTPUT="$OUTPUT_DIR/rfq_intake.md"

TECHNICAL_INPUT="$INTAKE_OUTPUT"
TECHNICAL_OUTPUT="$OUTPUT_DIR/technical_assessment.md"

QUOTE_INPUT_A="$INTAKE_OUTPUT"
QUOTE_INPUT_B="$TECHNICAL_OUTPUT"
QUOTE_OUTPUT="$OUTPUT_DIR/quotation.md"

FINAL_INPUT="$QUOTE_OUTPUT"
FINAL_OUTPUT="$OUTPUT_DIR/final_quotation.md"

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
# STAGE 1 — Intake Agent (no web search)
#############################################

echo "Running Intake Agent..."

INTAKE_PROMPT="You are the **Intake Agent** of the Possible RFQ & Project Assessment pipeline.

MANDATORY BEHAVIOR:
- You MUST NOT perform any web searches.
- You MUST parse the provided RFQ details and structure them into a professional brief.
- If input files are provided you MUST crawl and read through them to get a deep understanding.
- You MUST use MCP tools to write the structured document to: \`${INTAKE_OUTPUT}\`
- You MUST NOT finish without creating \`${INTAKE_OUTPUT}\`.

TASK:
- Analyze the following RFQ submission: \"${RFQ_DETAILS}\"
- Extract and list: client name, project type, project scope, key deliverables, budget range, timeline expectations, known constraints, and open questions.
- Organize the information into clearly labeled sections and highlight any assumptions.
- Keep the text response here brief; the full content goes into the output file."

opencode run "$INTAKE_PROMPT"

require_file "$INTAKE_OUTPUT"
echo "Intake Agent produced: ${INTAKE_OUTPUT}"
echo ""

#############################################
# STAGE 2 — Technical Assessment Agent
#############################################

echo "Running Technical Assessment Agent..."

TECHNICAL_PROMPT="You are the **Technical Assessment Agent** of the Possible RFQ & Project Assessment pipeline.

MANDATORY BEHAVIOR:
- You MUST read the intake document from: \`${TECHNICAL_INPUT}\`.
- You MUST use MCP tools to write the technical assessment to: \`${TECHNICAL_OUTPUT}\`.
- You MUST NOT finish without creating \`${TECHNICAL_OUTPUT}\`.
- You are allowed to perform web searches if needed for clarification.

TASK:
- Determine the proposed tech stack, team composition, delivery phases, and timeline feasibility.
- Identify technical risks, dependencies, and mitigation strategies.
- Estimate resource requirements (roles, hours) and note any assumptions.
- Keep this response brief; put the detailed assessment into the output file."

opencode run "$TECHNICAL_PROMPT"

require_file "$TECHNICAL_OUTPUT"
echo "Technical Assessment produced: ${TECHNICAL_OUTPUT}"
echo ""

#############################################
# STAGE 3 — Quotation Generator Agent (calculation based)
#############################################

echo "Running Quotation Generator Agent..."

QUOTE_PROMPT="You are the **Quotation Generator Agent** of the Possible RFQ & Project Assessment pipeline.

MANDATORY BEHAVIOR:
- You MUST read prior outputs: \`${QUOTE_INPUT_A}\` and \`${QUOTE_INPUT_B}\`.
- You MUST NOT perform any web searches.
- You MUST use MCP tools to write the quotation to: \`${QUOTE_OUTPUT}\`.
- You MUST NOT finish without creating \`${QUOTE_OUTPUT}\`.

TASK:
- Build a client-ready quotation that includes: executive summary, scope of work, phased timeline, pricing breakdown (labor, tools, contingency), payment terms, and assumptions.
- Ensure pricing aligns with the intake brief and technical assessment.
- Keep this reply short; place the full quotation in the output file."

opencode run "$QUOTE_PROMPT"

require_file "$QUOTE_OUTPUT"
echo "Quotation Generator produced: ${QUOTE_OUTPUT}"
echo ""

#############################################
# STAGE 4 — Review & Quality Check Agent (review only)
#############################################

echo "Running Review & Quality Check Agent..."

FINAL_PROMPT="You are the **Review & Quality Check Agent** of the Possible RFQ & Project Assessment pipeline.

MANDATORY BEHAVIOR:
- You MUST read the draft quotation from: \`${FINAL_INPUT}\`.
- You MUST NOT perform any web searches.
- You MUST use MCP tools to write the finalized quotation to: \`${FINAL_OUTPUT}\`.
- You MUST NOT finish without creating \`${FINAL_OUTPUT}\`.

TASK:
- Verify pricing consistency, ensure every client requirement is addressed, enhance tone and formatting, and add an executive summary if missing.
- Provide a polished, client-ready quotation in the output file.
- Keep your direct response minimal; the final document belongs in the output file."

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

echo "RFQ pipeline finished successfully!"
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
