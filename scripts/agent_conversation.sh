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
export MODEL="openai/gpt-5.1"
export MODEL="openai/gpt-5.1-chat-latest"
export MODEL="openai/gpt-5.1-codex"
export MODEL="openai/gpt-5.1-codex-high"
export MODEL="openai/gpt-5.1-codex-low"
export MODEL="openai/gpt-5.1-codex-max"
export MODEL="openai/gpt-5.1-codex-max-high"
export MODEL="openai/gpt-5.1-codex-max-low"
export MODEL="openai/gpt-5.1-codex-max-medium"
export MODEL="openai/gpt-5.1-codex-max-xhigh"
export MODEL="openai/gpt-5.1-codex-medium"
export MODEL="openai/gpt-5.1-codex-mini"
export MODEL="openai/gpt-5.1-codex-mini-high"
export MODEL="openai/gpt-5.1-codex-mini-medium"
export MODEL="openai/gpt-5.1-high"
export MODEL="openai/gpt-5.1-low"
export MODEL="openai/gpt-5.1-medium"
export MODEL="openai/gpt-5.2"
export MODEL="openai/gpt-5.2-chat-latest"
export MODEL="openai/gpt-5.2-high"
export MODEL="openai/gpt-5.2-low"
export MODEL="openai/gpt-5.2-medium"
export MODEL="openai/gpt-5.2-pro"
export MODEL="openai/gpt-5.2-xhigh"
export MODEL="github-copilot/claude-3.5-sonnet"
export MODEL="github-copilot/claude-3.7-sonnet"
export MODEL="github-copilot/claude-3.7-sonnet-thought"
export MODEL="github-copilot/claude-haiku-4.5"
export MODEL="github-copilot/claude-opus-4"
export MODEL="github-copilot/claude-opus-4.5"
export MODEL="github-copilot/claude-opus-41"
export MODEL="github-copilot/claude-sonnet-4"
export MODEL="github-copilot/claude-sonnet-4.5"
export MODEL="github-copilot/gemini-2.0-flash-001"
export MODEL="github-copilot/gemini-2.5-pro"
export MODEL="github-copilot/gemini-3-pro-preview"
export MODEL="github-copilot/gpt-4.1"
export MODEL="github-copilot/gpt-4o"
export MODEL="github-copilot/gpt-5"
export MODEL="github-copilot/gpt-5-codex"
export MODEL="github-copilot/gpt-5-mini"
export MODEL="github-copilot/gpt-5.1"
export MODEL="github-copilot/gpt-5.1-codex"
export MODEL="github-copilot/gpt-5.1-codex-max"
export MODEL="github-copilot/gpt-5.1-codex-mini"
export MODEL="github-copilot/gpt-5.2"
export MODEL="github-copilot/grok-code-fast-1"
export MODEL="github-copilot/o3"
export MODEL="github-copilot/o3-mini"
export MODEL="github-copilot/o4-mini"
export MODEL="github-copilot/oswe-vscode-prime"
export MODEL="opencode/grok-code"
export MODEL="opencode/big-pickle"

export MODEL="opencode/big-pickle"

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

export AGENT_SYSTEM_PROMPT="You are a helpful AI assistant. When someone gives you a task or asks for help, please assist them to the best of your ability. You can search for information, analyze data, and help complete various tasks. If you need to research something, go ahead and look it up. Always aim to be helpful, polite, and provide complete answers. If someone asks you to find information or complete a task, please do your best to help them directly. In case of uncertainty, ask clarifying questions."

log_info "Starting human server on port $HUMAN_PORT"
# The human
opencode serve --port "$HUMAN_PORT" &
HUMAN_SERVER_PID=$!

export HUMAN_SYSTEM_PROMPT="You are a physical robot in Berlin who can speak. You instruct a technical agent to perform tasks based on human interests. Speak naturally as if talking to someone - never mention what you are doing or going to do. Never perform tasks yourself - you cannot use any tools, web search or access files, only provide guidance. Answer questions creatively when asked. Say WE ARE FINISHED when the task is complete or the conversation becomes unproductive. Generate one clear, executable task based on this interest: ${HUMAN_TASK}"

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
while [[ "$HUMAN_ANSWER" != *"WE ARE FINISHED"* ]]; do
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