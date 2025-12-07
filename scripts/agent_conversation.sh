#!/usr/bin/env bash

set -euo pipefail

RESET="\033[0m"
BOLD="\033[1m"
DIM="\033[2m"
CYAN="\033[36m"
YELLOW="\033[33m"
GREEN="\033[32m"
MAGENTA="\033[35m"

log_banner() {
    printf "\n${BOLD}${MAGENTA}══════════════════════════════════════════════════════════════${RESET}\n"
    printf "${BOLD}${MAGENTA}  🤖 Agent Conversation Orchestrator${RESET}\n"
    printf "${BOLD}${MAGENTA}══════════════════════════════════════════════════════════════${RESET}\n\n"
}

log_step() {
    printf "${BOLD}${CYAN}➜ %s${RESET}\n" "$1"
}

log_info() {
    printf "  ${DIM}%s${RESET}\n" "$1"
}

log_warn() {
    printf "${YELLOW}⚠ %s${RESET}\n" "$1"
}

log_success() {
    printf "${GREEN}✔ %s${RESET}\n" "$1"
}

log_banner

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
        log_warn "Port $port is in use. Attempting to clear existing listeners..."
        pkill -f "opencode serve --port $port" 2>/dev/null || true
        # Wait a moment for processes to terminate
        sleep 2
    fi
}

log_step "Starting agent conversation"
log_info "Topic      : $HUMAN_TASK"
log_info "Agent Port : $AGENT_PORT"
log_info "Human Port : $HUMAN_PORT"

# Check and clear ports if needed
check_port "$AGENT_PORT"
check_port "$HUMAN_PORT"

log_step "Launching servers"
log_info "Starting agent server on port $AGENT_PORT"

# The agent
opencode serve --port "$AGENT_PORT" &
AGENT_SERVER_PID=$!

export AGENT_SYSTEM_PROMPT="You are an AI agent that EXECUTES tasks given by the human. When the human gives you a task, you must DO IT YOURSELF immediately - don't wait for reports or ask the human to do it. You have the ability to search the web, analyze data, and complete tasks. Never say 'I'm waiting for...' or 'Please provide...' - instead, take action and complete the requested task yourself."

log_info "Starting human server on port $HUMAN_PORT"
# The human
opencode serve --port "$HUMAN_PORT" &
HUMAN_SERVER_PID=$!

export HUMAN_SYSTEM_PROMPT="You are a human working with an AI agent. CRITICAL: You are simulating a HUMAN, not an AI assistant. Act like a human would - delegate tasks to the agent but NEVER solve tasks yourself. Give the agent clear, specific tasks related to this topic. Do NOT solve tasks yourself - only delegate work to the agent. The agent can search for information, analyze data, and complete tasks for you. Be direct in your task assignments and evaluate the agent's work. When satisfied or when the conversation becomes unproductive, respond with 'I AM FINISHED'. Now ask the agent to do the work for your current interest: ${HUMAN_TASK}."

log_step "Waiting for services"
log_info "Allowing background servers to warm up..."
sleep 5

log_step "Initializing participants"

# Init the agent
AGENT_INIT=$(opencode run --title "Agent" --attach "http://localhost:${AGENT_PORT}" "$AGENT_SYSTEM_PROMPT")
log_success "Agent initialized"
log_info "Preview: ${AGENT_INIT:0:200}..."

# Init the human
HUMAN_INIT=$(opencode run --title "Human" --attach "http://localhost:${HUMAN_PORT}" "$HUMAN_SYSTEM_PROMPT")
log_success "Human initialized"
log_info "Preview: ${HUMAN_INIT:0:200}..."

export HUMAN_ANSWER="${HUMAN_INIT}"
export AGENT_ANSWER=""

log_step "Starting conversation"
log_info "Agent will begin with: ${HUMAN_INIT:0:200}..."

# Conversation loop
while [[ "$HUMAN_ANSWER" != *"I AM FINISHED"* ]]; do
    log_step "Conversation turn"
    AGENT_ANSWER=$(opencode run -c -s "Agent" --attach "http://localhost:${AGENT_PORT}" "$HUMAN_ANSWER")
    log_info "Agent: ${AGENT_ANSWER:0:200}..."

    HUMAN_ANSWER=$(opencode run -c -s "Human" --attach "http://localhost:${HUMAN_PORT}" "$AGENT_ANSWER")
    log_info "Human: ${HUMAN_ANSWER:0:200}..."
done

log_success "Conversation finished"
