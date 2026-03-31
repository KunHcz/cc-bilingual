#!/bin/bash
# cc_hook.sh - Called by Claude Code hooks to log user/assistant messages
# Usage: cat | cc_hook.sh user        (UserPromptSubmit hook)
#        cat | cc_hook.sh assistant   (Stop hook)

EVENT_TYPE="${1:-}"
LOG_FILE="${CC_BILINGUAL_LOG:-/tmp/cc-bilingual.jsonl}"

# Read all of stdin into a variable, then pass via env to avoid injection issues
INPUT=$(cat)

# Use python3 for reliable JSON parsing and output
# Pass data via environment variables to avoid shell quoting issues
CC_HOOK_EVENT="$EVENT_TYPE" \
CC_HOOK_LOG="$LOG_FILE" \
CC_HOOK_INPUT="$INPUT" \
python3 -c '
import sys
import os
import json

event_type = os.environ.get("CC_HOOK_EVENT", "")
log_file = os.environ.get("CC_HOOK_LOG", "/tmp/cc-bilingual.jsonl")
input_data = os.environ.get("CC_HOOK_INPUT", "")

try:
    data = json.loads(input_data)
except (json.JSONDecodeError, ValueError):
    sys.exit(0)

if event_type == "user":
    text = data.get("prompt", "")
elif event_type == "assistant":
    text = data.get("response_text", "")
else:
    sys.exit(0)

if not text:
    sys.exit(0)

record = json.dumps({"role": event_type, "text": text}, ensure_ascii=False)
with open(log_file, "a", encoding="utf-8") as f:
    f.write(record + "\n")
'

exit 0
