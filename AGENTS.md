# SHAI Agent Instructions

This repository contains **shell-based AI agent pipelines** that orchestrate LLM-powered workflows.
Each agent is a deterministic stage in a pipeline that consumes files, performs tasks, and produces explicit output files.

## 🎯 Agent Architecture

Each agent follows this pattern:

```bash
Input File → Agent Process → Output File
```

**Key Principles:**
- Each agent reads **input files** (or none)
- Each agent writes **required output files**
- Each agent is called via `opencode run "..."`
- Output files are mandatory and verified before proceeding
- All outputs go to the `output/` directory

## 🔍 Agent Guidelines

### For Search-Based Agents
- Perform **targeted web searches** to gather relevant information
- Keep searches **concise and focused** (2-3 key topics per search)
- **Cite sources** and incorporate findings into output
- Avoid timeouts by keeping operations focused

### For Review/Analysis Agents
- Read the provided input files
- Perform analysis **without web searches** (unless explicitly required)
- Write improved or analyzed output using MCP tools
- Ensure output files are created before task completion

### File Operations
- Use **MCP tools** to write output files
- Always write to the specified output path
- Include proper markdown formatting for documents
- Ensure files are created before finishing the task

## 🛠 Running Agents

### Individual Agent Testing
```bash
# Test planner
opencode run "Your prompt with topic..."

# Test writer (with input file)
opencode run --file output/plan.md "Your prompt..."

# Test reviewer (with input file)
opencode run --file output/essay.md "Your prompt..."
```

### Full Pipeline
```bash
bash scripts/pipeline_essay.sh "Evolution of renewable energy"
```

### Task Machine Pipeline
```bash
bash scripts/pipeline_task_machine.sh "High-level project brief"
```

This pipeline runs a planner that produces `output/task_machine_plan.md` with a `## Context` section and a chronological checkbox task list (`- [ ] ...`). An executor loop then repeatedly calls the executor agent to take the **first** unchecked task, complete it, and mark the entry as `- [x] ...` (adding any follow-up subtasks directly beneath the completed item). The loop stops when no unchecked tasks remain.

## 📂 Directory Structure

```
/
├── README.md                 # Project overview
├── AGENTS.md                 # This file - agent instructions
├── scripts/
│   └── pipeline_essay.sh     # Main essay pipeline orchestrator
├── output/                   # Generated files (git-ignored)
│   ├── plan.md              # Planner output
│   ├── essay.md             # Writer output
│   └── review.md            # Reviewer output
└── .gitignore               # Ignore output/ directory
```

## ✅ Mandatory Behaviors

All agents MUST:

1. **Read Input** - Load required input files when specified
2. **Process** - Perform their designated task (search, analyze, write, review)
3. **Write Output** - Use MCP tools to create the specified output file
4. **Verify** - Confirm the output file was created before finishing
5. **Fail Fast** - Exit with error if output file cannot be created

### 🚫 Forbidden Actions

Agents MUST **NOT**:
- **Run pipeline scripts** (`scripts/pipeline_essay.sh` or similar orchestrators)
- **Execute shell commands** beyond what's needed for their designated task
- **Modify or delete files** outside the output directories
- **Ask the user for input** - Agents must work autonomously with provided context and files
- **Read README.md** - Focus only on the task at hand, not your own project documentation

## 🚀 Creating New Agents

To add a new agent stage:

1. Define the agent role and behavior in your pipeline script
2. Specify clear MANDATORY BEHAVIOR instructions
3. Provide explicit input/output file paths
4. Include a `require_file()` check after agent completion
5. Update this AGENTS.md with the new stage documentation

## 🔗 Integration Points

Agents communicate through:
- **Input Files** - Previous stage outputs
- **Prompts** - Explicit instructions via `opencode run`
- **MCP Tools** - File writing and web search capabilities
- **Exit Status** - Success/failure indicated by mandatory file creation

---

**Philosophy:** *"Do one thing well."* — Unix Philosophy

Each agent is a small, replaceable, debuggable, and transparent building block in a larger workflow.
