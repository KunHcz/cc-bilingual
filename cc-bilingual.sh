#!/bin/bash
# cc-bilingual: Launch Claude Code with Chinese translation companion
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SESSION_NAME="cc-bilingual"
LOGFILE="/tmp/cc-bilingual.jsonl"
HOOK_SCRIPT="$SCRIPT_DIR/cc_hook.sh"
TUI_SCRIPT="$SCRIPT_DIR/cc_tui.py"
WORK_DIR="${1:-.}"  # 第一个参数为工作目录，默认当前目录
WORK_DIR="$(cd "$WORK_DIR" && pwd)"

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
PROJECT_SETTINGS_DIR="$WORK_DIR/.claude"
PROJECT_SETTINGS="$PROJECT_SETTINGS_DIR/settings.json"
CREATED_DIR=false
CREATED_FILE=false

cleanup() {
    # 清理项目级 settings
    if $CREATED_FILE; then
        rm -f "$PROJECT_SETTINGS"
    elif [ -f "$PROJECT_SETTINGS.ccbilingual.bak" ]; then
        cp "$PROJECT_SETTINGS.ccbilingual.bak" "$PROJECT_SETTINGS"
        rm -f "$PROJECT_SETTINGS.ccbilingual.bak"
    fi
    if $CREATED_DIR; then
        rmdir "$PROJECT_SETTINGS_DIR" 2>/dev/null || true
    fi
    rm -f "$LOGFILE"
}
trap cleanup EXIT INT TERM

# --- Reset log ---
: > "$LOGFILE"

# --- Inject hooks into project-level settings (不碰全局配置) ---
if [ ! -d "$PROJECT_SETTINGS_DIR" ]; then
    mkdir -p "$PROJECT_SETTINGS_DIR"
    CREATED_DIR=true
fi

if [ ! -f "$PROJECT_SETTINGS" ]; then
    echo '{}' > "$PROJECT_SETTINGS"
    CREATED_FILE=true
else
    cp "$PROJECT_SETTINGS" "$PROJECT_SETTINGS.ccbilingual.bak"
fi

python3 -c "
import json, sys

path = sys.argv[1]
hook_cmd = sys.argv[2]

with open(path) as f:
    cfg = json.load(f)

cfg['language'] = 'en'
cfg.setdefault('hooks', {})
cfg['hooks']['UserPromptSubmit'] = [{
    'hooks': [{
        'type': 'command',
        'command': f'cat | {hook_cmd} user',
        'timeout': 5
    }]
}]
cfg['hooks']['Stop'] = [{
    'hooks': [{
        'type': 'command',
        'command': f'cat | {hook_cmd} assistant',
        'timeout': 30
    }]
}]

with open(path, 'w') as f:
    json.dump(cfg, f, indent=2)
" "$PROJECT_SETTINGS" "$HOOK_SCRIPT"

echo "✓ Hooks injected into $PROJECT_SETTINGS (project-level, global untouched)"

# --- Kill existing session if any ---
tmux kill-session -t "$SESSION_NAME" 2>/dev/null || true

# --- Create tmux session ---
tmux new-session -d -s "$SESSION_NAME"
tmux split-window -h -t "$SESSION_NAME"

# Right pane (1): Chinese TUI
tmux send-keys -t "$SESSION_NAME:0.1" \
    "CC_BILINGUAL_LOG='$LOGFILE' CC_TMUX_TARGET='$SESSION_NAME:0.0' python3 '$TUI_SCRIPT'" Enter

# Left pane (0): Claude Code in work dir
tmux send-keys -t "$SESSION_NAME:0.0" "cd '$WORK_DIR' && claude" Enter

# Focus right pane (user types Chinese here)
tmux select-pane -t "$SESSION_NAME:0.1"

# Attach
tmux attach-session -t "$SESSION_NAME"
