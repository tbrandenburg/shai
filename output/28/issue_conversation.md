# Issue #28 — GitMCP

## Original Post by @tbrandenburg

@task

1. Deeply read through https://gitmcp.io

2. Create an MCP configuration file for Claude Code which contains the gitmcp URLs to repos of following tech stack:

- Python package manager: uv
  - Python test framework: pytest
  - Node.JS test framework: Jest
  - Backend: FastAPI
  - Frontend: React + Vite + ShadCN
  - Agent Framework: pydantic-ai (https://ai.pydantic.dev/llms.txt)
  - Possible model provider: OpenAI, AWS Bedrock
  - Model self-hosting: ollama
  - Model repository: HuggingFace
  - Model memory: mem0 (https://github.com/mem0ai/mem0)
  - Model guardrails: guardrails-ai (https://github.com/guardrails-ai/guardrails & https://www.guardrailsai.com/docs/getting_started/guardrails_server/)
  - Model observability: LangFuse (https://langfuse.com/llms.txt)
  - Chatbot UI: chatbot-ui (https://github.com/ChristophHandschuh/chatbot-ui)
  - Web crawler: crawl4ai (https://github.com/unclecode/crawl4ai)
  - Document processing: docling (https://github.com/docling-project/docling)
  - Database: PostgreSQL (Supabase)
  - Vector Store: PGVector (Supabase Vector)
  - Storage: MinIO (local dev) -> Cloudflare R2 (production)
  - ORM: SQLAlchemy
  - Auth: JWT / OAuth2
  - Monitoring: Prometheus + Grafana
  - Logging: Loki
  - Error Tracking: Sentry
  - Scaling: Docker Swarm (early dev) -> K8s (public + at scale)
  - Deployment: Docker + Nginx + GitHub Actions
  - Publish (local dev): ngrok
  - Cloud: Vercel

## Comments
### Comment by @github-actions (2025-11-17T06:48:40Z)

🌿 **Branch created**: [`task-machine/issue-28-19420814943`](https://github.com/tbrandenburg/shai/tree/task-machine/issue-28-19420814943)

### Comment by @github-actions (2025-11-17T06:48:41Z)

## Context
The team must study the GitMCP documentation at https://gitmcp.io and deliver a Claude Code MCP configuration that maps the specified tech stack components (uv, FastAPI, React/Vite/ShadCN, etc.) to their official GitMCP repository URLs while reflecting the deployment and tooling expectations captured in `output/28/issue_conversation.md`.

## Role Descriptions
- **Tech Stack Researcher**: Investigates GitMCP resources and related project links to identify authoritative repository endpoints for every requested platform or tool. Prioritizes completeness, accurate citations, and well-organized notes. Communicates in concise bullet summaries that highlight any gaps or ambiguities.
- **Configuration Engineer**: Converts the curated research into a runnable Claude Code MCP configuration file that enumerates each tool’s GitMCP URL and relevant metadata. Focuses on correct schema usage, consistency, and clear inline comments where decisions need justification.
- **Quality Reviewer**: Verifies that the configuration satisfies all requirements, cross-checking against both the research notes and the original request. Emphasizes thorough validation, pointing out any unresolved risks or missing components in a short audit log.

## Chronologic Task List
- [x] Tech Stack Researcher Compile source brief — Read `output/28/issue_conversation.md` and https://gitmcp.io to list every tech stack item and its expected coverage, then summarize open questions or assumptions in `output/28/research_notes.md`.
  * Summary: Documented GitMCP behavior and full stack coverage notes plus open questions in `output/28/research_notes.md`.
- [x] Tech Stack Researcher Map repositories — Using the GitMCP site and linked resources, record the precise GitMCP repository URL (or document unavailability) for each stack component, storing the structured table plus citations in `output/28/repo_catalog.md`.
  * Summary: Cataloged every stack element with GitHub + GitMCP URLs in `repo_catalog.md`, noting the Guardrails server docs lack a GitMCP endpoint.
- [x] Configuration Engineer Draft Claude Code MCP file — Read `output/28/research_notes.md` and `output/28/repo_catalog.md`, then build a complete Claude Code MCP configuration (JSON or YAML) that enumerates all stack components with their gitmcp URLs, authentication settings if needed, and explanatory comments, saving it to `output/28/claude_code_mcp_config.json`.
  * Summary: Generated `claude_code_mcp_config.json` with every requested gitmcp.io endpoint plus a gap note for non-GitHub Guardrails server docs.
- [x] Quality Reviewer Audit configuration — Compare `output/28/claude_code_mcp_config.json` against `output/28/research_notes.md`, `output/28/repo_catalog.md`, and `output/28/issue_conversation.md`, document verification results plus any follow-up actions in `output/28/review_log.md`, and flag unresolved gaps directly in that log.
  * Summary: Logged audit findings in `output/28/review_log.md`, confirming full coverage and flagging Guardrails server docs as the lone open gap.


### Comment by @tbrandenburg (2025-11-17T06:53:25Z)

@task

In the generated claude code MCP configuration there is an error.
MCPs are configured like:

```

{
  "mcpServers": {
    "pydantic-ai Docs": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "https://gitmcp.io/pydantic/pydantic-ai"
      ]
    }
  }
}
```

