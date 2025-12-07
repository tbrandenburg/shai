#!/usr/bin/env bash

set -euo pipefail

# Define ports
export AGENT_PORT=4096
export HUMAN_PORT=4097

# Get the human task from the first argument or prompt for one
if [ -z "${1:-}" ]; then
    read -p "Enter the task you want to discuss: " HUMAN_TASK
else
    HUMAN_TASK="$1"
fi

# Ensure background servers are terminated when the script exits
cleanup() {
    kill "$AGENT_SERVER_PID" "$HUMAN_SERVER_PID" 2>/dev/null || true
}
trap cleanup EXIT

# Function to check if a port is available
check_port() {
    local port=$1
    if netstat -tuln 2>/dev/null | grep -q ":$port "; then
        echo "Port $port is already in use. Killing processes on this port..."
        pkill -f "opencode serve --port $port" 2>/dev/null || true
        # Wait a moment for processes to terminate
        sleep 2
    fi
}

echo "Starting agent conversation for: $HUMAN_TASK"

# Check and clear ports if needed
check_port "$AGENT_PORT"
check_port "$HUMAN_PORT"

echo "Starting agent server on port $AGENT_PORT..."

# The agent
opencode serve --port "$AGENT_PORT" &
AGENT_SERVER_PID=$!

export AGENT_SYSTEM_PROMPT="You are an AI agent. The human will give you tasks to complete. Take action to fulfill their requests - search for information, analyze data, provide answers, or complete whatever task they assign. Be proactive and helpful. Don't wait for instructions or refer to yourself in third person."

echo "Starting human server on port $HUMAN_PORT..."
# The human
opencode serve --port "$HUMAN_PORT" &
HUMAN_SERVER_PID=$!

export HUMAN_SYSTEM_PROMPT="You are a human working with an AI agent. Your topic of interest is: ${HUMAN_TASK}. Give the agent clear, specific tasks related to this topic. Do NOT solve tasks yourself - only delegate work to the agent. The agent can search for information, analyze data, and complete tasks for you. Be direct in your task assignments and evaluate the agent's work. When satisfied or when the conversation becomes unproductive, respond with 'I AM FINISHED'."

echo "Waiting 5 seconds for servers to fully start..."
sleep 5

echo "Initializing agent and human participants..."

# Init the agent
AGENT_INIT=$(opencode run --title "Agent" --attach "http://localhost:${AGENT_PORT}" "$AGENT_SYSTEM_PROMPT")
echo "Agent initialized: ${AGENT_INIT:0:200}..."

# Init the human
HUMAN_INIT=$(opencode run --title "Human" --attach "http://localhost:${HUMAN_PORT}" "$HUMAN_SYSTEM_PROMPT")
echo "Human initialized: ${HUMAN_INIT:0:200}..."

export HUMAN_ANSWER="$HUMAN_TASK"
export AGENT_ANSWER=""

echo "Starting conversation loop..."
echo "Human will begin with: $HUMAN_TASK"

# Conversation loop
while [[ "$HUMAN_ANSWER" != *"I AM FINISHED"* ]]; do
    echo "---"
    AGENT_ANSWER=$(opencode run -c -s "Agent" --attach "http://localhost:${AGENT_PORT}" "$HUMAN_ANSWER")
    echo "Agent: ${AGENT_ANSWER:0:200}..."
    
    HUMAN_ANSWER=$(opencode run -c -s "Human" --attach "http://localhost:${HUMAN_PORT}" "$AGENT_ANSWER")
    echo "Human: ${HUMAN_ANSWER:0:200}..."
done

echo "--- Finished ---"
