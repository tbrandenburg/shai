# FastA2A Research Notes

### Source: Pydantic AI Docs — `docs/a2a.md`
- Citation: https://github.com/pydantic/pydantic-ai/blob/main/docs/a2a.md (Context7 `/pydantic/pydantic-ai`)
- Overview: FastA2A is an agnostic Agent2Agent (A2A) protocol implementation for Python built on Starlette + Pydantic, enabling interoperable AI agent services.
- Installation Guidance: `pip/uv-add fasta2a` installs the FastA2A server runtime directly, while `pip/uv-add 'pydantic-ai-slim[a2a]'` installs Pydantic AI plus the `a2a` extra, pulling FastA2A automatically — ideal when wrapping agents with the A2A surface.
- API Behavior: Any `pydantic_ai.Agent` can expose an ASGI-compliant FastA2A endpoint via `agent.to_a2a()`, which turns the agent into a Starlette-compatible app responding to A2A protocol payloads. Developers then launch it with an ASGI server such as `uvicorn agent_to_a2a:app --host 0.0.0.0 --port 8000`.
- Usage Scenario: Use FastA2A when you need to publish a single agent as an interoperable microservice that other coordinators can invoke through the standardized protocol without sharing Python process state.

### Source: Context7 Snapshot — `pydantic/pydantic-ai/llms.txt`
- Citation: https://context7.com/pydantic/pydantic-ai/llms.txt (Context7 `/pydantic/pydantic-ai`)
- Overview: Demonstrates orchestrating multi-agent workflows by turning specialized agents into FastA2A services via `pydantic_ai.a2a.agent_to_a2a` and invoking them from a coordinator agent.
- API Behavior: `agent_to_a2a(agent, service_name='...')` wraps an agent as a callable FastA2A service; the returned object exposes `.call(...)` for remote invocation, while `AgentWorker` can manage concurrent service calls.
- Usage Scenario: Build modular research/writer pipelines where each worker runs behind FastA2A, and a coordinator agent registers lightweight `@coordinator.tool` functions that proxy to those services. This lets heterogeneous model backends collaborate while communicating through the A2A wire format.
- Context7 Exposure: The llms.txt feed includes runnable Python demonstrating both service registration and coordinator tooling, giving downstream roles a reference for replicating the same pattern without re-querying GitHub.
