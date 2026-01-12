The "natural next evolution / abstraction" of SHAI would be a unified command-line interface (`shai`) that simplifies pipeline execution. This wrapper script abstracts away the specific script paths, handles ID generation, and provides a consistent way to pass input (either directly or from a file) to any pipeline.

This new `shai` command will make the project significantly easier to use and remember, fulfilling your goal of a "super-easy to remember" daily tool by centralizing command syntax.

To implement this, we will perform the following steps:

1.  **Add a new "Unified SHAI CLI" section to `README.md`** describing the new command and its benefits.
2.  **Create a new executable `shai` wrapper script** in the project root directory. This script will be the single entry point.
3.  **Modify `scripts/pipeline_essay.sh`** to accept `--id` and `--file` arguments and manage its output in a consistent, file-based manner, aligning it with `pipeline_task_machine.sh` for a uniform experience.

---

### Step 1: Update `README.md`

We will add a new section to your `README.md` to introduce the unified `shai` CLI and update the example usage for the Essay Pipeline.

<tool_code>
FILE_EDIT_INSTR: README.md
INSERT_AFTER: ## 🚀 Features

## ✨ Unified SHAI CLI (Next Evolution)

To make SHAI even easier to use and remember for daily command-line tasks, we're introducing a unified `shai` command-line interface. This wrapper script simplifies pipeline execution by handling script paths, ID generation, and consistent input parsing.

Now, instead of remembering specific script locations and argument formats, you can run any SHAI pipeline with a single, clear command:

```bash
shai <pipeline_type> <prompt_text | --file <path>> [--id <identifier>]
```

### 🚀 Key Benefits

-   **Single Entry Point:** One command to rule them all: `shai`.
-   **Intuitive Syntax:** Easy to remember `shai <type> <input> [options]`.
-   **Automatic ID Generation:** Unique output directories created by default if `--id` is not specified.
-   **Consistent Input:** Use direct text or `--file` for any pipeline (now fully supported after minor pipeline script adaptations).
-   **Future-Proof:** Easily extensible to new pipelines (`shai research`, `shai code`, etc.).

### Usage Examples

```bash
# Run the Task Machine pipeline with a direct prompt
shai task "Design and build a simple blog website with user authentication."

# Run the Task Machine pipeline with input from a file and a custom ID
shai task --file ./my_project_brief.md --id blog-project-v2

# Run the Essay pipeline with a topic
shai essay "The impact of artificial intelligence on modern education systems."

# Run the Essay pipeline with a topic from a file and a specific ID
shai essay --file ./essay_topic_long.txt --id ai-education-report
```

This abstraction significantly reduces cognitive load and makes SHAI a truly "super-easy to remember" daily tool. To achieve full consistency, minor adjustments are made to existing pipeline scripts to adopt the `--id` and `--file` conventions.
---
INSERT_AFTER: Call it via:

```bash
shai essay "Scouts in Sweden"
# Or with a custom ID:
shai essay "Scouts in Sweden" --id sweden-scouts-report
# Or with file input:
shai essay --file sweden_scouts_topic.txt --id sweden-scouts-file
```
</tool_code>

### Step 2: Create the `shai` Wrapper Script

Create a new executable Bash script named `shai` in the root directory of your project (at the same level as `README.md` and the `scripts` folder).

<tool_code>
FILE_EDIT_INSTR: shai
CREATE_FILE: True
```bash
#!/usr/bin/env bash
# shai - A unified CLI for SHAI pipelines

set -euo pipefail

# --- Configuration ---
# Map pipeline types to their script paths
declare -A PIPELINES=(
  ["task"]="./scripts/pipeline_task_machine.sh"
  ["essay"]="./scripts/pipeline_essay.sh"
  # Add more pipelines here as they are created
)

# --- Helper Functions ---
generate_id() {
  date +%Y%m%d-%H%M%S-%N | cut -c1-22 # YYYYMMDD-HHMMSS-NNNNNNNNN (approx. 22 chars)
}

usage() {
  echo "Usage: shai <pipeline_type> <prompt_text | --file <path>> [--id <identifier>]"
  echo ""
  echo "Available pipeline types:"
  for type in "${!PIPELINES[@]}"; do
    echo "  - $type"
  done | sort # Sort for consistent output
  echo ""
  echo "Examples:"
  echo "  shai task \"Create a weather dashboard app\""
  echo "  shai task --file requirements.md --id project-456"
  echo "  shai essay \"Scouts in Sweden\""
  echo "  shai essay --file essay_topic.txt --id ai-education-report"
  exit 1
}

# --- Main Logic ---

# Check if any arguments are provided or if --help is requested
if [[ "$#" -eq 0 ]] || [[ "$1" == "--help" ]] || [[ "$1" == "-h" ]]; then
  usage
fi

# Initialize variables
pipeline_type=""
input_source="" # Either "text" or "file"
input_value=""
pipeline_id=""

# Parse pipeline type
pipeline_type="$1"
shift

if [[ ! -v "PIPELINES[$pipeline_type]" ]]; then
  echo "Error: Unknown pipeline type '$pipeline_type'."
  usage
fi

# Parse remaining arguments
while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --id)
      if [[ -n "$pipeline_id" ]]; then echo "Error: --id specified multiple times."; usage; fi
      pipeline_id="$2"
      shift 2
      ;;
    --file)
      if [[ -n "$input_value" ]]; then echo "Error: Input already provided (text or --file)."; usage; fi
      if [[ ! -f "$2" ]]; then echo "Error: Input file '$2' not found."; exit 1; fi
      input_source="file"
      input_value="$2"
      shift 2
      ;;
    *)
      if [[ -n "$input_value" ]]; then echo "Error: Multiple text inputs provided."; usage; fi
      input_source="text"
      input_value="$1"
      shift
      ;;
  esac
done

# Ensure input is provided
if [[ -z "$input_value" ]]; then
  echo "Error: No input provided for the pipeline."
  usage
fi

# If no ID provided, generate one
if [[ -z "$pipeline_id" ]]; then
  pipeline_id=$(generate_id)
fi

# Construct the command for the specific pipeline script
script_path="${PIPELINES[$pipeline_type]}"
declare -a script_args=()

# All pipeline scripts should now uniformly accept --id and either a positional argument or --file.
# The existing pipeline_task_machine.sh already does this.
# The pipeline_essay.sh will be modified to do this.

if [[ "$input_source" == "file" ]]; then
  script_args+=("--file" "$input_value")
else
  script_args+=("$input_value")
fi
script_args+=("--id" "$pipeline_id") # Pass the ID to the underlying script

echo "--- SHAI RUN ---"
echo "Pipeline: $pipeline_type (ID: $pipeline_id)"
echo "Input: $input_source ('$input_value')"
echo "Executing: $script_path ${script_args[@]}"
echo "----------------"

# Execute the target pipeline script
exec "$script_path" "${script_args[@]}"
```
</tool_code>

Make the `shai` script executable:
`chmod +x shai`

### Step 3: Modify `scripts/pipeline_essay.sh`

To align `pipeline_essay.sh` with the new `shai` CLI's `--id` and `--file` argument parsing, and to enforce file-based input/output for consistency, we need to update its content.

<tool_code>
FILE_EDIT_INSTR: scripts/pipeline_essay.sh
REPLACE_ALL: True
```bash
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
  ESSAY_TOPAY_CONTENT="$INPUT_ARG"
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
WRITER_PROMPT_FILE="$OUTPUT_DIR/writer_prompt.md"
ESSAY_DRAFT_FILE="$OUTPUT_DIR/essay_draft.md"
REVIEWER_PROMPT_FILE="$OUTPUT_DIR/reviewer_prompt.md"
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
</tool_code>

After these changes, you can now use the new `shai` command directly from your terminal, making SHAI much more intuitive and "super-easy to remember." For example, to run an essay pipeline:

```bash
./shai essay "The history of the internet"
```
Or for a task machine pipeline:
```bash
./shai task "Create a markdown document summarizing AI trends" --id "ai-summary-q3"
```
