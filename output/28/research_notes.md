# Research Notes — Tech Stack Researcher

## GitMCP Source Brief (https://gitmcp.io)
- GitMCP exposes any public GitHub repository as a remote MCP server by swapping the domain to `gitmcp.io`, enabling Claude Code and similar tools to ingest repo context instantly.
- AI tools consume default repo documents (README, `llms.txt`, `llms-full.txt`, docs) without extra setup, so every stack item must resolve to a public GitHub repository for consistent MCP coverage.
- Custom MCP endpoints can also target GitHub Pages (`username.gitmcp.io/repo`), meaning documentation-only repos are still viable if code repos are unavailable.

## Tech Stack Coverage Requirements (source: output/28/issue_conversation.md)
| Category | Component | Expected Coverage Notes |
| --- | --- | --- |
| Package Mgmt | uv | Official repo that defines Python package manager behavior; ensure MCP link exposes uv docs.
| Testing | pytest | Core repo for pytest to pull fixtures/plugins context.
| Testing | Jest | Facebook/Meta maintained repo for Jest JavaScript testing framework.
| Backend | FastAPI | Official tiangolo FastAPI repository for API definitions and docs.
| Frontend | React | Meta's React repo for component APIs.
| Frontend | Vite | Vite build tool repo for configuration context.
| Frontend | ShadCN | shadcn/ui repo (UI components) to support design system references.
| Agent Framework | pydantic-ai | GitHub repo referenced via https://ai.pydantic.dev/llms.txt (likely pydantic/pydantic-ai).
| Model Providers | OpenAI | Need repo that best represents OpenAI API MCP endpoint (e.g., openai/openai-python?).
| Model Providers | AWS Bedrock | Identify AWS samples repo exposing Bedrock (e.g., aws-samples/amazon-bedrock-samples) if official MCP-ready target exists.
| Model Runtime | ollama | Official ollama/ollama repo.
| Model Hub | HuggingFace | huggingface/transformers or a repo describing HF MCP server; confirm best canonical repo.
| Memory | mem0 | Provided repo https://github.com/mem0ai/mem0.
| Guardrails | guardrails-ai | Guardrails AI repo plus server docs repo noted in issue.
| Observability | LangFuse | Use repo linked via https://langfuse.com/llms.txt (langfuse/langfuse).
| Chat UI | chatbot-ui | Provided repo https://github.com/ChristophHandschuh/chatbot-ui.
| Web Crawler | crawl4ai | Provided repo https://github.com/unclecode/crawl4ai.
| Document Proc | docling | Provided repo https://github.com/docling-project/docling.
| Database | PostgreSQL (Supabase) | Likely supabase/supabase repo with Postgres config context.
| Vector Store | PGVector (Supabase Vector) | Determine supabase-community/pgvector or supabase/vector repo.
| Storage | MinIO | Official MinIO server repo for local dev.
| Storage | Cloudflare R2 | Cloudflare's repo coverage limited—need best public sample or docs repo demonstrating R2 usage.
| ORM | SQLAlchemy | SQLAlchemy/SQLAlchemy repo for ORM configuration reference.
| Auth | JWT / OAuth2 | Need canonical spec or sample repo (maybe auth0/node-jsonwebtoken + oauthlib?). Clarify expectations.
| Monitoring | Prometheus | Prometheus/prometheus repo plus Grafana/grafana for dashboards.
| Logging | Loki | grafana/loki repo for log aggregation.
| Error Tracking | Sentry | getsentry/sentry repo representing on-prem server.
| Orchestration | Docker Swarm | moby/moby docs or docker/docs repo focusing on swarm instructions.
| Orchestration | Kubernetes | kubernetes/kubernetes repo for cluster config context.
| Deployment | Docker | docker/cli or docker/docs to cover container build workflow.
| Deployment | Nginx | nginx/nginx (mirror) or official doc repo.
| Deployment | GitHub Actions | actions/toolkit or github/docs for workflows.
| Publish | ngrok | ngrok-edge examples repo (if public) for tunneling guidance.
| Cloud | Vercel | vercel/vercel repo referencing deployment platform.

## Open Questions & Assumptions
- Need confirmation whether model providers (OpenAI, AWS Bedrock) should point to official SDK repos or dedicated llms.txt endpoints; GitMCP requires GitHub repos, so SDK repos may be acceptable proxies.
- JWT/OAuth2 lacks a single canonical repo; may require selecting widely adopted reference implementations (e.g., jsonwebtoken/jsonwebtoken, oauthlib/oauthlib).
- Cloudflare R2 and ngrok are primarily services; must verify if official sample repos exist to satisfy GitMCP linkage, else document as unavailable.
- For Supabase-specific items (PostgreSQL, PGVector, storage), determine whether a single supabase/supabase repo can represent multiple capabilities or if separate repos exist.
- Need to ensure guardrails-ai includes both the main code repo and server/docs repo mentioned; clarify whether both need MCP entries.
