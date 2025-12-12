# Agent Conversation Architecture

The `agent_conversation.sh` script spins up two independent OpenCode JSON-RPC services—one for the agent and one for the human advocate—and relays their messages over persistent sessions until the human ends the dialogue.

```
                       opencode JSON-RPC (localhost)
┌──────────────────────────────────────────────────────────────────────────┐
│                              Host shell                                  │
└──────────────────────────────────────────────────────────────────────────┘
        | serve --port 4096                             | serve --port 4097
        v                                               v
┌────────────────────────┐                     ┌────────────────────────┐
│ Agent server            │                    │ Human server           │
│ (AGENT_PORT=4096)       │                    │ (HUMAN_PORT=4097)      │
│ AGENT_SYSTEM_PROMPT     │                    │ HUMAN_SYSTEM_PROMPT    │
└────────────────────────┘                     └────────────────────────┘
        ^                                               ^
        | init: opencode run --attach :4096             | init: opencode run --attach :4097
        | → AGENT_SESSION_ID                            | → HUMAN_SESSION_ID
        |                                               |
        +---------------------- conversation loop ------------------------+
        |                                                                |
        | opencode run -s AGENT_SESSION_ID --attach :4096                |
        |   (agent crafts reply)                                         |
        |<--------------------------------------------------------------+|
        | opencode run -s HUMAN_SESSION_ID --attach :4097               ||
        |   (human advocate responds)                                   ||
        +-------------------------------------------------------------->|
        |                                                                |
        +----------------------------------------------------------------+
                          until HUMAN says "I AM FINISHED"
        |
        +--> summaries via opencode run on each session
        +--> exports → sessions/agent_session_*.json & human_session_*.json
```

Key notes:
- Both services are isolated; each maintains its own session state and system prompt.
- All dialogue turns are JSON-RPC calls made through `opencode run --attach http://localhost:<PORT>`.
- Ports are checked and cleared before startup, and sessions are exported after the conversation concludes.
