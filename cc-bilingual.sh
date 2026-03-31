#!/bin/bash
# cc-bilingual: Launch Claude Code with Chinese translation companion
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SESSION_NAME="cc-bilingual"
LOGFILE="/tmp/cc-bilingual.jsonl"
HOOK_SCRIPT="$SCRIPT_DIR/cc_hook.sh"
TUI_SCRIPT="$SCRIPT_DIR/cc_tui.py"
SETTINGS_FILE="$HOME/.claude/settings.json"
BACKUP_FILE="$HOME/.claude/settings.json.ccbilingual.bak"

# --- Dependency check ---
for cmd in tmux python3 claude; do
    if ! command -v "$cmd" &>/dev/null; then
        echo "Error: '$cmd' is required but not found."
        [ "$cmd" = "tmux" ] && echo "  Install: brew install tmux"
        [ "$cmd" = "claude" ] && echo "  Install: npm install -g @anthropic-ai/claude-code"
        exit 1
    fi
done

# --- Cleanup on exit ---
cleanup() {
    if [ -f "$BACKUP_FILE" ]; then
        cp "$BACKUP_FILE" "$SETTINGS_FILE"
        rm -f "$BACKUP_FILE"
    fi
    rm -f "$LOGFILE"
}
trap cleanup EXIT INT TERM

# --- Reset log ---
: > "$LOGFILE"

# --- Backup and inject hooks ---
cp "$SETTINGS_FILE" "$BACKUP_FILE"

python3 -c "
import json, sys

path = sys.argv[1]
hook_cmd = sys.argv[2]

with open(path) as f:
    cfg = json.load(f)

cfg['hooks'] = {
    'UserPromptSubmit': [{
        'hooks': [{
            'type': 'command',
            'command': f'cat | {hook_cmd} user',
            'timeout': 5
        }]
    }],
    'Stop': [{
        'hooks': [{
            'type': 'command',
            'command': f'cat | {hook_cmd} assistant',
            'timeout': 30
        }]
    }]
}

with open(path, 'w') as f:
    json.dump(cfg, f, indent=2)
" "$SETTINGS_FILE" "$HOOK_SCRIPT"

echo "✓ Hooks configured"

# --- Kill existing session if any ---
tmux kill-session -t "$SESSION_NAME" 2>/dev/null || true

# --- Create tmux session ---
tmux new-session -d -s "$SESSION_NAME"
tmux split-window -h -t "$SESSION_NAME"

# Right pane (1): Chinese TUI
tmux send-keys -t "$SESSION_NAME:0.1" \
    "CC_BILINGUAL_LOG='$LOGFILE' CC_TMUX_TARGET='$SESSION_NAME:0.0' python3 '$TUI_SCRIPT'" Enter

# Left pane (0): Claude Code  (pass any extra args to claude)
tmux send-keys -t "$SESSION_NAME:0.0" "claude $*" Enter

# Focus right pane (user types Chinese here)
tmux select-pane -t "$SESSION_NAME:0.1"

# Attach
tmux attach-session -t "$SESSION_NAME"
