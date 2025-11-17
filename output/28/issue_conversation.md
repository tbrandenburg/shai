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
