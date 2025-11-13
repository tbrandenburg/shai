# 🫖 **SHAI - Shell AI Agents**

<img width="640" height="640" alt="image" src="https://github.com/user-attachments/assets/edd5f668-f095-465b-90f3-1c5287d86a5c" />

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

OUTPUT_FILE="$1"

PROMPT=$(cat <<EOF
You are the PLANNING STAGE.

MANDATORY:
- Perform multiple web searches to understand the topic.
- Extract relevant facts, debates, and context.
- Write a structured outline to: ${OUTPUT_FILE} using MCP tools.
- Do NOT finish your task without writing it.

Return only a summary of what you created.
EOF
)

opencode run --prompt "$PROMPT"
[[ -f "$OUTPUT_FILE" ]] || { echo "Planner failed: $OUTPUT_FILE missing"; exit 1; }
```

## 🖇️ Example Pipeline Script

``` bash
#!/usr/bin/env bash
set -euo pipefail

TOPIC="$1"

./agents/planner.sh output/plan.md "$TOPIC"
./agents/writer.sh output/plan.md output/essay.md
./agents/reviewer.sh output/essay.md output/review.md

echo "Pipeline finished. See output/ for results."
```

## ⚙️ Web-Research Agents

Include instructions like:

`You MUST perform multiple web searches to gather facts and context.`

## 🧪 Testing Your Pipeline

``` bash
bash agents/planner.sh output/plan.md "Evolution of renewable energy"
bash agents/writer.sh output/plan.md output/essay.md
bash agents/reviewer.sh output/essay.md output/review.md
```

Or run the entire chain:

``` bash
bash scripts/essay_pipeline.sh "The role of AI in climate modeling"
```

## 🌗 Icons & Branding

SHAI ships with a simple chai-inspired icon for: - Light mode
- Dark mode (transparent background)

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
