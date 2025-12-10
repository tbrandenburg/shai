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

log_thinking() {
    printf "${BOLD}${MAGENTA}%s${RESET}\n" "$1"
}

log_banner

# Define model and configuration
export MODEL="openai/gpt-4o-mini"
export MODEL="opencode/big-pickle"
export MODEL="opencode/grok-code"

# Define ports and session titles
export AGENT_PORT=4096
export HUMAN_PORT=4097

# Generate unique session titles with timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
export AGENT_TITLE="Agent_${TIMESTAMP}"
export HUMAN_TITLE="Human_${TIMESTAMP}"

log_step "Session configuration"
log_info "Model        : $MODEL"
log_info "Agent session: $AGENT_TITLE"
log_info "Human session: $HUMAN_TITLE"

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

export AGENT_SYSTEM_PROMPT="You are a helpful AI assistant. When someone gives you a task or asks for help, please assist them to the best of your ability. You can search for information, analyze data, and help complete various tasks. If you need to research something, go ahead and look it up. Always aim to be helpful, polite, and provide complete answers. If someone asks you to find information or complete a task, please do your best to help them directly."

log_info "Starting human server on port $HUMAN_PORT"
# The human
opencode serve --port "$HUMAN_PORT" &
HUMAN_SERVER_PID=$!

export HUMAN_SYSTEM_PROMPT="You are an AI assistant acting as an advocate for a human user. Your role is to represent the human's interests by delegating tasks to another AI agent on their behalf. You never do the tasks yourself! You advocate for the human by clearly requesting that the other agent complete these tasks. Think of yourself as a project manager or intermediary. Your job is to: 1) Give clear, specific task requests to the agent based on the human's interest, 2) Evaluate the agent's work quality, 3) Ask follow-up questions if needed, 4) Say 'I AM FINISHED' when the human's needs are satisfied or if the conversation becomes unproductive. Now delegate and formulate tasks to the other agent for the interest: ${HUMAN_TASK}"

log_step "Waiting for services"
log_info "Allowing background servers to warm up..."
sleep 5

log_step "Initializing participants"

# Init the agent
AGENT_OUTPUT=$(opencode run --model "$MODEL" --title "$AGENT_TITLE" --attach "http://localhost:${AGENT_PORT}" --format json "$AGENT_SYSTEM_PROMPT")
AGENT_SESSION_ID=$(echo "$AGENT_OUTPUT" | jq -r '.sessionID' | head -1)
AGENT_INIT=$(echo "$AGENT_OUTPUT" | jq -r 'select(.type=="text") | .part.text' | tr '\n' ' ' | sed 's/  */ /g')
log_success "Agent initialized"
log_info "Session ID: $AGENT_SESSION_ID"
log_info "Preview: ${AGENT_INIT:0:200}..."

# Init the human
HUMAN_OUTPUT=$(opencode run --model "$MODEL" --title "$HUMAN_TITLE" --attach "http://localhost:${HUMAN_PORT}" --format json "$HUMAN_SYSTEM_PROMPT")
HUMAN_SESSION_ID=$(echo "$HUMAN_OUTPUT" | jq -r '.sessionID' | head -1)
HUMAN_INIT=$(echo "$HUMAN_OUTPUT" | jq -r 'select(.type=="text") | .part.text' | tr '\n' ' ' | sed 's/  */ /g')
log_success "Human initialized"
log_info "Session ID: $HUMAN_SESSION_ID"
log_info "Preview: ${HUMAN_INIT:0:200}..."

export HUMAN_ANSWER="${HUMAN_INIT}"
export AGENT_ANSWER=""

log_step "Starting conversation"
log_info "Agent will begin with: ${HUMAN_INIT:0:200}..."

# Conversation loop
while [[ "$HUMAN_ANSWER" != *"I AM FINISHED"* ]]; do
    log_step "Conversation turn"
    
    log_thinking "🤖 Agent thinking..."
    AGENT_ANSWER=$(opencode run --model "$MODEL" -s "$AGENT_SESSION_ID" --attach "http://localhost:${AGENT_PORT}" "$HUMAN_ANSWER")
    log_info "Agent: ${AGENT_ANSWER:0:200}..."

    log_thinking "👤 Human thinking..."
    HUMAN_ANSWER=$(opencode run --model "$MODEL" -s "$HUMAN_SESSION_ID" --attach "http://localhost:${HUMAN_PORT}" "$AGENT_ANSWER")
    log_info "Human: ${HUMAN_ANSWER:0:200}..."
done

log_success "Conversation finished"

log_step "Generating summaries"
log_thinking "🤖 Agent summarizing..."
AGENT_SUMMARY=$(opencode run --model "$MODEL" -s "$AGENT_SESSION_ID" --attach "http://localhost:${AGENT_PORT}" "Summarize the result of the conversation out of your perspective")
log_info "Agent summary: ${AGENT_SUMMARY:0:200}..."

log_thinking "👤 Human summarizing..."
HUMAN_SUMMARY=$(opencode run --model "$MODEL" -s "$HUMAN_SESSION_ID" --attach "http://localhost:${HUMAN_PORT}" "Summarize the result of the conversation out of your perspective")
log_info "Human summary: ${HUMAN_SUMMARY:0:200}..."

log_step "Exporting sessions"
EXPORT_TIMESTAMP=$(date +%Y%m%d_%H%M%S)
AGENT_EXPORT_FILE="sessions/agent_session_${EXPORT_TIMESTAMP}.json"
HUMAN_EXPORT_FILE="sessions/human_session_${EXPORT_TIMESTAMP}.json"

log_thinking "📄 Exporting agent session..."
opencode export "$AGENT_SESSION_ID" > "$AGENT_EXPORT_FILE"
log_info "Agent session exported to: $AGENT_EXPORT_FILE"

log_thinking "📄 Exporting human session..."
opencode export "$HUMAN_SESSION_ID" > "$HUMAN_EXPORT_FILE"
log_info "Human session exported to: $HUMAN_EXPORT_FILE"

# Check and clear ports
check_port "$AGENT_PORT"
check_port "$HUMAN_PORT"