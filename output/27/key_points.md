# FastA2A Key Points

## Feature Overview
1. FastA2A provides a protocol-agnostic Agent2Agent server built on Starlette and Pydantic so any `pydantic_ai.Agent` can be exposed as an interoperable microservice reachable via the standardized A2A wire format. *(Source: pydantic-ai/docs/a2a.md)*
2. The Context7 llms snapshot documents how FastA2A enables modular multi-agent orchestration by letting coordinators treat each specialized agent as a remotely callable service without sharing Python process state. *(Source: Context7 llms.txt)*

## Integration Requirements
1. Installation paths split between adding the dedicated `fasta2a` runtime or pulling `pydantic-ai-slim[a2a]`, ensuring teams can either deploy standalone servers or bundle A2A exposure alongside the main framework. *(Source: pydantic-ai/docs/a2a.md)*
2. Calling `agent.to_a2a()` (or `pydantic_ai.a2a.agent_to_a2a(...)`) converts the agent into an ASGI app that can be launched under `uvicorn`, and the wrapper also returns client helpers like `.call(...)` for coordinators. *(Sources: pydantic-ai/docs/a2a.md, Context7 llms.txt)*
3. Coordinators register lightweight tools that proxy to these services, while AgentWorker instances juggle concurrent calls—this pattern is illustrated in the llms snapshot and should be mirrored when composing pipelines. *(Source: Context7 llms.txt)*

## Operational Quirks & Guidance
1. FastA2A is best suited when you need network-isolated agents (e.g., different infra or hardware) to interoperate; expose only the minimal agent surface to avoid state bleed. *(Source: pydantic-ai/docs/a2a.md)*
2. Treat the Context7 snapshot as the canonical code reference—the included Python snippets remove the need to browse GitHub while preserving the citation trail for downstream roles. *(Source: Context7 llms.txt)*
