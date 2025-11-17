# GitMCP Repository Catalog

Each GitMCP endpoint simply swaps a GitHub repository domain to `gitmcp.io`, so the following table captures the authoritative repositories for every requested stack component along with the ready-to-use Claude Code MCP URLs and any availability caveats.

| Category | Component | GitHub Repository | GitMCP URL | Notes | Source |
| --- | --- | --- | --- | --- | --- |
| Package Mgmt | uv | [astral-sh/uv](https://github.com/astral-sh/uv) | [gitmcp.io/astral-sh/uv](https://gitmcp.io/astral-sh/uv) | Official Python packaging tool maintained by Astral. | [1] |
| Testing | pytest | [pytest-dev/pytest](https://github.com/pytest-dev/pytest) | [gitmcp.io/pytest-dev/pytest](https://gitmcp.io/pytest-dev/pytest) | Core pytest runner/plugins for Python tests. | [2] |
| Testing | Jest | [jestjs/jest](https://github.com/jestjs/jest) | [gitmcp.io/jestjs/jest](https://gitmcp.io/jestjs/jest) | Meta-maintained JavaScript test framework. | [3] |
| Backend | FastAPI | [tiangolo/fastapi](https://github.com/tiangolo/fastapi) | [gitmcp.io/tiangolo/fastapi](https://gitmcp.io/tiangolo/fastapi) | Official FastAPI server/runtime definitions. | [4] |
| Frontend | React | [facebook/react](https://github.com/facebook/react) | [gitmcp.io/facebook/react](https://gitmcp.io/facebook/react) | Canonical React component runtime. | [5] |
| Frontend | Vite | [vitejs/vite](https://github.com/vitejs/vite) | [gitmcp.io/vitejs/vite](https://gitmcp.io/vitejs/vite) | Vite build tool repo for dev/prod bundling. | [6] |
| Frontend | ShadCN/UI | [shadcn-ui/ui](https://github.com/shadcn-ui/ui) | [gitmcp.io/shadcn-ui/ui](https://gitmcp.io/shadcn-ui/ui) | Component library definitions powering ShadCN UI. | [7] |
| Agent Framework | pydantic-ai | [pydantic/pydantic-ai](https://github.com/pydantic/pydantic-ai) | [gitmcp.io/pydantic/pydantic-ai](https://gitmcp.io/pydantic/pydantic-ai) | Official agent framework backing https://ai.pydantic.dev/. | [8] |
| Model Provider | OpenAI | [openai/openai-python](https://github.com/openai/openai-python) | [gitmcp.io/openai/openai-python](https://gitmcp.io/openai/openai-python) | Python SDK exposes API schema & examples for OpenAI. | [9] |
| Model Provider | AWS Bedrock | [aws-samples/amazon-bedrock-samples](https://github.com/aws-samples/amazon-bedrock-samples) | [gitmcp.io/aws-samples/amazon-bedrock-samples](https://gitmcp.io/aws-samples/amazon-bedrock-samples) | Official AWS samples demonstrating Bedrock integrations. | [10] |
| Model Runtime | ollama | [ollama/ollama](https://github.com/ollama/ollama) | [gitmcp.io/ollama/ollama](https://gitmcp.io/ollama/ollama) | Runtime for self-hosting LLMs locally. | [11] |
| Model Hub | HuggingFace | [huggingface/transformers](https://github.com/huggingface/transformers) | [gitmcp.io/huggingface/transformers](https://gitmcp.io/huggingface/transformers) | Transformer model zoo & APIs covering HF use cases. | [12] |
| Memory | mem0 | [mem0ai/mem0](https://github.com/mem0ai/mem0) | [gitmcp.io/mem0ai/mem0](https://gitmcp.io/mem0ai/mem0) | Repository cited in the request for conversational memory. | [13] |
| Guardrails | guardrails-ai | [guardrails-ai/guardrails](https://github.com/guardrails-ai/guardrails) | [gitmcp.io/guardrails-ai/guardrails](https://gitmcp.io/guardrails-ai/guardrails) | Core Guardrails library referenced in the brief. | [14] |
| Guardrails | Guardrails Server Docs | — (docs only) | N/A | Vendor hosts server docs outside GitHub, so no GitMCP endpoint; keep using web docs. | [15] |
| Observability | LangFuse | [langfuse/langfuse](https://github.com/langfuse/langfuse) | [gitmcp.io/langfuse/langfuse](https://gitmcp.io/langfuse/langfuse) | LangFuse server + docs repo linked via llms.txt. | [16] |
| Chat UI | chatbot-ui | [ChristophHandschuh/chatbot-ui](https://github.com/ChristophHandschuh/chatbot-ui) | [gitmcp.io/ChristophHandschuh/chatbot-ui](https://gitmcp.io/ChristophHandschuh/chatbot-ui) | Requested UI shell for chat experiences. | [17] |
| Web Crawler | crawl4ai | [unclecode/crawl4ai](https://github.com/unclecode/crawl4ai) | [gitmcp.io/unclecode/crawl4ai](https://gitmcp.io/unclecode/crawl4ai) | Provides crawler pipelines and docs. | [18] |
| Document Processing | docling | [docling-project/docling](https://github.com/docling-project/docling) | [gitmcp.io/docling-project/docling](https://gitmcp.io/docling-project/docling) | Core document parsing toolkit. | [19] |
| Database | PostgreSQL (Supabase) | [supabase/supabase](https://github.com/supabase/supabase) | [gitmcp.io/supabase/supabase](https://gitmcp.io/supabase/supabase) | Supabase monorepo includes Postgres config & tooling. | [20] |
| Vector Store | PGVector (Supabase Vector) | [supabase-community/pgvector](https://github.com/supabase-community/pgvector) | [gitmcp.io/supabase-community/pgvector](https://gitmcp.io/supabase-community/pgvector) | Supabase-maintained PGVector extensions. | [21] |
| Storage | MinIO | [minio/minio](https://github.com/minio/minio) | [gitmcp.io/minio/minio](https://gitmcp.io/minio/minio) | Local S3-compatible object storage server. | [22] |
| Storage | Cloudflare R2 | [cloudflare/r2-examples](https://github.com/cloudflare/r2-examples) | [gitmcp.io/cloudflare/r2-examples](https://gitmcp.io/cloudflare/r2-examples) | Official sample repo covering R2 usage. | [23] |
| ORM | SQLAlchemy | [sqlalchemy/sqlalchemy](https://github.com/sqlalchemy/sqlalchemy) | [gitmcp.io/sqlalchemy/sqlalchemy](https://gitmcp.io/sqlalchemy/sqlalchemy) | Primary ORM referenced by the stack. | [24] |
| Auth | JWT (PyJWT) | [jpadilla/pyjwt](https://github.com/jpadilla/pyjwt) | [gitmcp.io/jpadilla/pyjwt](https://gitmcp.io/jpadilla/pyjwt) | Canonical JWT signing/verification lib for Python. | [25] |
| Auth | OAuth2 (OAuthlib) | [oauthlib/oauthlib](https://github.com/oauthlib/oauthlib) | [gitmcp.io/oauthlib/oauthlib](https://gitmcp.io/oauthlib/oauthlib) | Widely used OAuth toolkit used by FastAPI ecosystems. | [26] |
| Monitoring | Prometheus | [prometheus/prometheus](https://github.com/prometheus/prometheus) | [gitmcp.io/prometheus/prometheus](https://gitmcp.io/prometheus/prometheus) | Metrics collection server for monitoring. | [27] |
| Monitoring | Grafana | [grafana/grafana](https://github.com/grafana/grafana) | [gitmcp.io/grafana/grafana](https://gitmcp.io/grafana/grafana) | Dashboard/visualization stack for Prometheus metrics. | [28] |
| Logging | Loki | [grafana/loki](https://github.com/grafana/loki) | [gitmcp.io/grafana/loki](https://gitmcp.io/grafana/loki) | Grafana Loki log aggregation backend. | [29] |
| Error Tracking | Sentry | [getsentry/sentry](https://github.com/getsentry/sentry) | [gitmcp.io/getsentry/sentry](https://gitmcp.io/getsentry/sentry) | On-prem Sentry for error monitoring. | [30] |
| Orchestration | Docker Swarm | [moby/moby](https://github.com/moby/moby) | [gitmcp.io/moby/moby](https://gitmcp.io/moby/moby) | Swarm mode is part of the upstream Moby engine repo. | [31] |
| Orchestration | Kubernetes | [kubernetes/kubernetes](https://github.com/kubernetes/kubernetes) | [gitmcp.io/kubernetes/kubernetes](https://gitmcp.io/kubernetes/kubernetes) | Canonical K8s control plane repo. | [32] |
| Deployment | Docker | [docker/cli](https://github.com/docker/cli) | [gitmcp.io/docker/cli](https://gitmcp.io/docker/cli) | CLI/engine interface for container builds & pushes. | [33] |
| Deployment | Nginx | [nginx/nginx](https://github.com/nginx/nginx) | [gitmcp.io/nginx/nginx](https://gitmcp.io/nginx/nginx) | Official Nginx reverse-proxy source. | [34] |
| Deployment | GitHub Actions | [actions/toolkit](https://github.com/actions/toolkit) | [gitmcp.io/actions/toolkit](https://gitmcp.io/actions/toolkit) | Provides reusable components for Actions workflows. | [35] |
| Publish (Local Dev) | ngrok | [ngrok/ngrok-python](https://github.com/ngrok/ngrok-python) | [gitmcp.io/ngrok/ngrok-python](https://gitmcp.io/ngrok/ngrok-python) | Official Python SDK for tunneling services. | [36] |
| Cloud | Vercel | [vercel/vercel](https://github.com/vercel/vercel) | [gitmcp.io/vercel/vercel](https://gitmcp.io/vercel/vercel) | Deployment platform monorepo w/ builder configs. | [37] |

### References
[1] https://github.com/astral-sh/uv  
[2] https://github.com/pytest-dev/pytest  
[3] https://github.com/jestjs/jest  
[4] https://github.com/tiangolo/fastapi  
[5] https://github.com/facebook/react  
[6] https://github.com/vitejs/vite  
[7] https://github.com/shadcn-ui/ui  
[8] https://github.com/pydantic/pydantic-ai  
[9] https://github.com/openai/openai-python  
[10] https://github.com/aws-samples/amazon-bedrock-samples  
[11] https://github.com/ollama/ollama  
[12] https://github.com/huggingface/transformers  
[13] https://github.com/mem0ai/mem0  
[14] https://github.com/guardrails-ai/guardrails  
[15] https://www.guardrailsai.com/docs/getting_started/guardrails_server/  
[16] https://github.com/langfuse/langfuse  
[17] https://github.com/ChristophHandschuh/chatbot-ui  
[18] https://github.com/unclecode/crawl4ai  
[19] https://github.com/docling-project/docling  
[20] https://github.com/supabase/supabase  
[21] https://github.com/supabase-community/pgvector  
[22] https://github.com/minio/minio  
[23] https://github.com/cloudflare/r2-examples  
[24] https://github.com/sqlalchemy/sqlalchemy  
[25] https://github.com/jpadilla/pyjwt  
[26] https://github.com/oauthlib/oauthlib  
[27] https://github.com/prometheus/prometheus  
[28] https://github.com/grafana/grafana  
[29] https://github.com/grafana/loki  
[30] https://github.com/getsentry/sentry  
[31] https://github.com/moby/moby  
[32] https://github.com/kubernetes/kubernetes  
[33] https://github.com/docker/cli  
[34] https://github.com/nginx/nginx  
[35] https://github.com/actions/toolkit  
[36] https://github.com/ngrok/ngrok-python  
[37] https://github.com/vercel/vercel
