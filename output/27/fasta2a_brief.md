# FastA2A Brief

## What FastA2A Is
FastA2A turns any `pydantic_ai.Agent` into a protocol-agnostic Agent2Agent (A2A) microservice by wrapping it in a Starlette/ASGI server so other coordinators can call it over the standardized A2A wire format without sharing Python process state. (pydantic-ai/docs/a2a.md; Context7 llms.txt)

## Why It Matters
- Lets multi-agent pipelines stay modular: each specialist can run on separate infra or hardware and still interoperate through uniform A2A calls. (Context7 llms.txt)
- Encourages least-privilege design by exposing only the agent’s public surface rather than full runtime state, improving isolation for sensitive workloads. (pydantic-ai/docs/a2a.md)
- Ships with client helpers so coordinators can treat remote agents like local callables, simplifying orchestration logic. (pydantic-ai/docs/a2a.md)

## How To Use It
1. Install either the minimal `fasta2a` runtime or the bundled `pydantic-ai-slim[a2a]`, depending on whether you need only the server or the whole framework. (pydantic-ai/docs/a2a.md)
2. Convert an agent by calling `agent.to_a2a()` (or `pydantic_ai.a2a.agent_to_a2a(...)`), which returns an ASGI app plus client shims like `.call(...)`; serve it with `uvicorn`. (pydantic-ai/docs/a2a.md; Context7 llms.txt)
3. Have your coordinator (or any AgentWorker) register lightweight tools that proxy to the exposed service, mirroring the pattern captured in the Context7 llms snapshot. (Context7 llms.txt)
4. When documenting or extending the setup, reference the Context7 MCP `llms` snapshot directly—it embeds the canonical FastA2A examples so you can cite them without browsing GitHub. (Context7 llms.txt)

## Access Via Context7 MCP
- Use the Context7 MCP `llms` snapshot as the authoritative source; it contains the FastA2A code snippets and orchestration examples cited above.
- Pair those excerpts with the pydantic FastA2A doc surfaced in Context7 (`pydantic-ai/docs/a2a.md`) for installation and API details. Together they provide everything needed to explain or operationalize FastA2A inside the pipeline.
