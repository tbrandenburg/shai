#!/usr/bin/env bash

set -euo pipefail

# Get the human task from the first argument or prompt for one
if [ -z "${1:-}" ]; then
    read -p "Enter the task you want to discuss: " HUMAN_TASK
else
    HUMAN_TASK="$1"
fi

# The agent
export AGENT_PORT=4096
opencode serve --port "$AGENT_PORT" &
AGENT_SERVER_PID=$!

export AGENT_SYSTEM_PROMPT="You are an AI agent collaborating with a human. Provide thoughtful, concise replies based on their messages without adding unnecessary context."

# The human
export HUMAN_PORT=4097
opencode serve --port "$HUMAN_PORT" &
HUMAN_SERVER_PID=$!

export HUMAN_SYSTEM_PROMPT="You are a human collaborator working with an agent. Your today's idea is: ${HUMAN_TASK}. Wait for the next input."

# Ensure background servers are terminated when the script exits
cleanup() {
    kill "$AGENT_SERVER_PID" "$HUMAN_SERVER_PID" 2>/dev/null || true
}
trap cleanup EXIT

# Init the agent
opencode run --title "Agent" --attach "http://localhost:${AGENT_PORT}" "$AGENT_SYSTEM_PROMPT"

# Init the human
opencode run --title "Human" --attach "http://localhost:${HUMAN_PORT}" "$HUMAN_SYSTEM_PROMPT"

export HUMAN_ANSWER="$HUMAN_TASK"
export AGENT_ANSWER=""

# Conversation loop
while [[ "$HUMAN_ANSWER" != *"I AM FINISHED"* ]]; do
    AGENT_ANSWER=$(opencode run -c -s "Agent" --attach "http://localhost:${AGENT_PORT}" "$HUMAN_ANSWER")
    HUMAN_ANSWER=$(opencode run -c -s "Human" --attach "http://localhost:${HUMAN_PORT}" "$AGENT_ANSWER")
done
