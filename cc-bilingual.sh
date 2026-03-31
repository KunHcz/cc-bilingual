#!/bin/bash
# cc-bilingual: Launch Claude Code with Chinese translation companion
# No hooks, no settings modification. Watches CC's own conversation log.
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SESSION_NAME="cc-bilingual"
TUI_SCRIPT="$SCRIPT_DIR/cc_tui.py"
WORK_DIR="${1:-.}"
WORK_DIR="$(cd "$WORK_DIR" && pwd)"

# CC conversation log dir: ~/.claude/projects/-Users-hooke-Desktop-develop/
PROJECT_PATH=$(echo "$WORK_DIR" | tr '/' '-')
CONV_DIR="$HOME/.claude/projects/$PROJECT_PATH"

# --- Dependency check ---
for cmd in tmux python3 claude; do
    if ! command -v "$cmd" &>/dev/null; then
        echo "Error: '$cmd' is required but not found."
        [ "$cmd" = "tmux" ] && echo "  Install: brew install tmux"
        [ "$cmd" = "claude" ] && echo "  Install: npm install -g @anthropic-ai/claude-code"
        exit 1
    fi
done

# Record existing JSONL files so TUI can identify the NEW one
EXISTING_FILES="/tmp/cc-bilingual-existing.txt"
ls "$CONV_DIR"/*.jsonl 2>/dev/null | sort > "$EXISTING_FILES" || true

# --- Kill existing session ---
tmux kill-session -t "$SESSION_NAME" 2>/dev/null || true

# --- Create tmux session ---
tmux new-session -d -s "$SESSION_NAME"
tmux set-option -t "$SESSION_NAME" mouse on
tmux split-window -h -t "$SESSION_NAME"

# Right pane (1): Chinese TUI
tmux send-keys -t "$SESSION_NAME:0.1" \
    "CC_CONV_DIR='$CONV_DIR' CC_EXISTING_FILES='$EXISTING_FILES' CC_TMUX_TARGET='$SESSION_NAME:0.0' python3 '$TUI_SCRIPT'" Enter

# Left pane (0): Claude Code
tmux send-keys -t "$SESSION_NAME:0.0" "cd '$WORK_DIR' && claude" Enter

# Focus right pane
tmux select-pane -t "$SESSION_NAME:0.1"

# Attach
tmux attach-session -t "$SESSION_NAME"
