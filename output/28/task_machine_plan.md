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
