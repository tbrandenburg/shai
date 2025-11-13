# 🫖 **SHAI - Shell AI Agents**

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
- 📁 **Strict file-based input/output** --- no hidden conversation
  state
- 🔎 **Optional web-enabled agents** for research stages
- 🔐 **Mandatory output verification** (stops pipeline if file
  missing)
- 🪢 **Pipeable workflows**---think Unix pipelines, but with agents
- 💬 Works with any LLM CLI

## ✨ Why This Project Matters

Running agents with shell scripts unlocks powerful capabilities:

- **🔄 Reusable bash scripts** – Write once, run anywhere: locally, in CI/CD pipelines, or scheduled workflows
- **🏗️ GitHub Actions integration** – Embed agent pipelines directly into GitHub workflows for automated content generation, analysis, and reviews
- **🛠️ Full MCP tooling** – Access file operations, web search, and custom tools from within deterministic shell scripts
- **📊 Testable & debuggable** – Each agent stage produces explicit output files; inspect, validate, and iterate independently
- **⚡ No infrastructure overhead** – No servers, containers, or external services; pure bash + LLM CLI orchestration
- **🔗 Composable automation** – Chain agents into sophisticated pipelines: research → planning → writing → review → publication

Perfect for content workflows, code generation, research automation and intelligent document processing at scale.

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

## 🧠 Example Agent: Planner

``` bash
#!/usr/bin/env bash
set -euo pipefail

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
- Keep your text response brief."

opencode run "$PLANNER_PROMPT"

[[ -f "$PLANNER_OUTPUT" ]] || { echo "Planner failed: $PLANNER_OUTPUT missing"; exit 1; }
```

## 🖇️ Example Pipeline Script

``` bash
#!/usr/bin/env bash
set -euo pipefail

TOPIC="${1:-}"

if [[ -z "$TOPIC" ]]; then
  echo "Usage: $0 \"Essay topic\""
  exit 1
fi

OUTPUT_DIR="output"
mkdir -p "$OUTPUT_DIR"

PLANNER_OUTPUT="$OUTPUT_DIR/plan.md"
WRITER_OUTPUT="$OUTPUT_DIR/essay.md"
REVIEWER_OUTPUT="$OUTPUT_DIR/review.md"

# Helper: Mandatory output enforcement
require_file() {
  local filename="$1"
  if [[ ! -f "$filename" ]]; then
    echo "ERROR: Required output file '$filename' was NOT created."
    exit 1
  fi
}

# Run each agent in sequence
opencode run "Your PLANNER prompt here..."
require_file "$PLANNER_OUTPUT"

opencode run "Your WRITER prompt here..."
require_file "$WRITER_OUTPUT"

opencode run "Your REVIEWER prompt here..."
require_file "$REVIEWER_OUTPUT"

echo "Pipeline finished successfully!"
```

## 🧪 Testing Your Pipeline

``` bash
bash scripts/pipeline_essay.sh "Evolution of renewable energy"
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
-   Any CLI-based LLM runner
-   Optional MCP tools for file writing

## 🙌 Contributing

PRs and issues welcome!

## 📄 License

MIT --- enjoy your chai.
