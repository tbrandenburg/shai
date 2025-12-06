# 🫖 **SHAI - Shell AI Agents**

Orchestrate agents with shell scripts - and drink a chai :wink:

<div align="center">
  <img width="640" height="640" alt="image" src="https://github.com/user-attachments/assets/edd5f668-f095-465b-90f3-1c5287d86a5c" />
</div>

## Lightweight agent orchestration using plain shell scripts

**SHAI** (Shell-AI / sh-ai) is a minimal, file-based agent orchestration
framework built entirely around **shell scripts**.
No servers, no daemons, no Docker - just **Bash + your preferred LLM
CLI + MCPs**.

It enables you to create deterministic, debuggable, Unix-style pipelines
of AI "agents" where each stage consumes and produces **explicit
files** (`plan.md`, `essay.md`, `review.md`, etc.), making automation
transparent and reproducible.

## 🚀 Features

- 🧩 **Composable agent stages** written as standard shell scripts
- 📁 **Strict file-based input/output** --- no hidden conversation state
- 🎯 **Multi-role task execution** with role-based task assignments
- 📊 **Real-time progress tracking** with task completion counters
- 🆔 **Parallel execution support** with unique ID-based output directories
- 🔎 **Optional web-enabled agents** for research stages
- 🔐 **Mandatory output verification** (stops pipeline if file missing)
- 🪢 **Pipeable workflows**---think Unix pipelines, but with agents
- 💬 Works with any LLM CLI
- 🤖 **GitHub Actions integration** for automated issue processing

## ✨ Why This Project Matters

Running agents with shell scripts unlocks powerful capabilities:

- **🔄 Reusable bash scripts** – Write once, run anywhere: locally, in CI/CD pipelines, or scheduled workflows
- **🏗️ GitHub Actions integration** – Embed agent pipelines directly into GitHub workflows for automated content generation, analysis, and reviews
- **🛠️ Full MCP tooling** – Access file operations, web search, and custom tools from within deterministic shell scripts
- **📊 Testable & debuggable** – Each agent stage produces explicit output files; inspect, validate, and iterate independently
- **⚡ No infrastructure overhead** – No servers, containers, or external services; pure bash + LLM CLI orchestration
- **🔗 Composable automation** – Chain agents into sophisticated pipelines: research → planning → writing → review → publication

Perfect for content workflows, code generation, research automation and intelligent document processing at scale.

## 📦 Example: Task Machine Pipeline

    User request → Planner → Executor Loop → Completed tasks

The **Task Machine** is SHAI's most advanced pipeline, featuring multi-role task execution with real-time progress tracking:

```bash
# Basic usage
./scripts/pipeline_task_machine.sh "Create a weather dashboard app"

# With unique ID for parallel execution
./scripts/pipeline_task_machine.sh "Build user authentication" --id "auth-123"

# Using input file
./scripts/pipeline_task_machine.sh --file requirements.md --id "project-456"
```

### 🎯 Task Machine Features

- **Multi-role execution**: Tasks are assigned to specific roles (Developer, Designer, Analyst, etc.)
- **Progress tracking**: Real-time updates show `completed/total` tasks and remaining work
- **Dynamic adaptation**: New subtasks can be added during execution
- **Parallel execution**: Use `--id` to run multiple instances without conflicts
- **GitHub integration**: Automatically triggered by `@task` comments in issues

### Example Task Machine Output Structure

```
output/project-123/
├── task_request.txt           # Original request
└── task_machine_plan.md       # Plan with role assignments and progress
```

Each task in the plan follows this format:
```markdown
- [ ] [Developer] Set up project structure — Create folders, package.json, and basic configuration files
- [x] [Designer] Create wireframes — Design user interface mockups for main screens
```

## 📦 Example: Essay Pipeline

    User topic → Planner → Writer → Reviewer → Final output

Call it via:

```bash
./scripts/pipeline_essay.sh "Scouts in Sweden"
```

Each agent:

-   Receives a *single* input file (or none)
-   Produces a *single* required output file
-   Is called by a simple `opencode run "..."`
-   Uses MCP tools to write output files internally

## 🧠 Example Agent: Task Machine Planner

``` bash
#!/usr/bin/env bash
set -euo pipefail

# Task Machine Planner with role-based assignments
read -r -d '' PLANNER_PROMPT <<EOF || true
You are the **TASK MACHINE PLANNER** in a two-stage pipeline.

MANDATORY BEHAVIOR:
- Use MCP tools to read the user's goal from \`${CONTEXT_FILE}\`
- Use MCP tools to read the multi-role template from \`${TEMPLATE_FILE}\`
- Produce a markdown document written to: \`${PLAN_FILE}\`
- The document MUST contain three sections:
  1. \`## Context\` summarizing the overall objective
  2. \`## Role Descriptions\` for each role needed
  3. \`## Chronologic Task List\` with role assignments
- Every task MUST specify which role is responsible:
  \`- [ ] [Role Name] Task description — detailed instructions\`
- Keep the plan lightweight and avoid unnecessary busywork
- This workflow is UNSUPERVISED: make decisions autonomously

TASK: Create the plan for the request in \`${CONTEXT_FILE}\`
EOF

opencode run "$PLANNER_PROMPT"

[[ -f "$PLAN_FILE" ]] || { echo "Planner failed: $PLAN_FILE missing"; exit 1; }
```

## 🔄 Example Agent: Task Machine Executor

``` bash
# Executor loop with progress tracking
iteration=1
while grep -q "\\[ \\]" "$PLAN_FILE"; do
  # Count progress
  total_tasks=$(grep -c "^- \[.\]" "$PLAN_FILE" || echo "0")
  completed_tasks=$(grep -c "^- \[x\]" "$PLAN_FILE" || echo "0")
  remaining_tasks=$(grep -c "^- \[ \]" "$PLAN_FILE" || echo "0")
  
  echo "Iteration ${iteration}... (${completed_tasks}/${total_tasks} completed, ${remaining_tasks} remaining)"
  
  # Execute first unchecked task
  opencode run "$EXECUTOR_PROMPT"
  
  iteration=$((iteration + 1))
done

echo "All tasks completed! (${final_completed_tasks}/${final_total_tasks} tasks finished)"
```

## 🖇️ Example Pipeline Script

``` bash
#!/usr/bin/env bash
set -euo pipefail

# Task Machine Pipeline with ID support
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
if [[ -n "$ID_ARG" ]]; then
  OUTPUT_DIR="output/${ID_ARG}"
else
  OUTPUT_DIR="output"
fi
mkdir -p "$OUTPUT_DIR"

PLAN_FILE="$OUTPUT_DIR/task_machine_plan.md"

# Helper: Mandatory output enforcement
require_file() {
  local filename="$1"
  if [[ ! -f "$filename" ]]; then
    echo "ERROR: Required output file '$filename' was NOT created."
    exit 1
  fi
}

# Run planner
opencode run "$PLANNER_PROMPT"
require_file "$PLAN_FILE"

# Run executor loop with progress tracking
iteration=1
while grep -q "\\[ \\]" "$PLAN_FILE"; do
  # Progress tracking
  total_tasks=$(grep -c "^- \[.\]" "$PLAN_FILE" || echo "0")
  completed_tasks=$(grep -c "^- \[x\]" "$PLAN_FILE" || echo "0")
  remaining_tasks=$(grep -c "^- \[ \]" "$PLAN_FILE" || echo "0")
  
  echo "Running executor iteration ${iteration}... (${completed_tasks}/${total_tasks} completed, ${remaining_tasks} remaining)"
  
  opencode run "$EXECUTOR_PROMPT"
  require_file "$PLAN_FILE"
  
  iteration=$((iteration + 1))
done

echo "All tasks completed!"
```

## 🤖 GitHub Actions Integration

SHAI includes automated GitHub Actions integration for issue-based task processing:

```yaml
# Triggered by @task comments in issues
on:
  issue_comment:
    types: [created]
  issues:
    types: [opened, edited, reopened]

jobs:
  task-machine:
    runs-on: ubuntu-latest
    steps:
      - name: Run task machine pipeline
        run: |
          bash scripts/pipeline_task_machine.sh --file "$PROMPT_FILE" --id "$ISSUE_NUMBER"
```

Features:
- **Admin-only execution**: Only repository admins can trigger `@task`
- **Automatic ID assignment**: Uses issue number for unique output directories
- **Progress tracking**: Shows real-time task completion in issue comments
- **File isolation**: Each issue gets its own output directory (`output/123/`, `output/456/`)

## 🧪 Testing Your Pipeline

``` bash
# Test task machine locally
bash scripts/pipeline_task_machine.sh "Create a todo app"

# Test with ID for parallel execution
bash scripts/pipeline_task_machine.sh "Build API endpoints" --id "backend-dev"

# Test essay pipeline
bash scripts/pipeline_essay.sh "Evolution of renewable energy"

# Test with file input
bash scripts/pipeline_task_machine.sh --file requirements.md --id "project-123"
```

Or test individual stages with your own prompts.

## ⚙️ Web-Research Agents

Include instructions like:

````
You MUST perform multiple web searches to gather facts and context.
...
- **TIMEOUT SAFETY:** Keep searches focused on 2-3 key topics per search to avoid timeouts.
````

## 📜 Philosophy

> *"Do one thing well."* --- Unix Philosophy

Agents are small, replaceable, debuggable, and transparent.

## 🛠 Requirements

-   Bash ≥ 4
-   [opencode](https://github.com/sst/opencode) installed and a default model configured
-   Any CLI-based LLM runner
-   Optional MCP tools for file writing

## ⚠️ Important Disclaimer

**For experimental use only; using this script as a bot in violation of any service's terms is prohibited and may be illegal.**

## 🙌 Contributing

PRs and issues welcome!

## 📄 License

MIT

## Credits

Credits to [Cole Medin](https://github.com/coleam00/) for some of his ideas used here.

## 🫖 Enjoy your shai!
