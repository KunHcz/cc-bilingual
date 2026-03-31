#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
HOOK="$SCRIPT_DIR/cc_hook.sh"
LOGFILE="/tmp/cc-bilingual-test.jsonl"

rm -f "$LOGFILE"
touch "$LOGFILE"

# Test 1: UserPromptSubmit event
echo '{"prompt": "Help me write a sort", "session_id": "test123"}' | \
    CC_BILINGUAL_LOG="$LOGFILE" bash "$HOOK" user

RESULT=$(cat "$LOGFILE")
echo "$RESULT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
assert data['role'] == 'user', f'Expected user, got {data[\"role\"]}'
assert data['text'] == 'Help me write a sort', f'Wrong text: {data[\"text\"]}'
print('Test 1 PASSED: user event')
"

# Test 2: Stop event
echo '{"response_text": "Sure, here is a quicksort.", "session_id": "test123"}' | \
    CC_BILINGUAL_LOG="$LOGFILE" bash "$HOOK" assistant

RESULT=$(tail -1 "$LOGFILE")
echo "$RESULT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
assert data['role'] == 'assistant', f'Expected assistant, got {data[\"role\"]}'
assert 'quicksort' in data['text'], f'Wrong text: {data[\"text\"]}'
print('Test 2 PASSED: assistant event')
"

# Test 3: Empty prompt should not write
echo '{"prompt": "", "session_id": "test123"}' | \
    CC_BILINGUAL_LOG="$LOGFILE" bash "$HOOK" user

LINE_COUNT=$(wc -l < "$LOGFILE" | tr -d ' ')
if [ "$LINE_COUNT" = "2" ]; then
    echo "Test 3 PASSED: empty prompt ignored"
else
    echo "Test 3 FAILED: expected 2 lines, got $LINE_COUNT"
    exit 1
fi

# Test 4: Unknown event type should exit cleanly
echo '{"prompt": "test"}' | \
    CC_BILINGUAL_LOG="$LOGFILE" bash "$HOOK" unknown
LINE_COUNT2=$(wc -l < "$LOGFILE" | tr -d ' ')
if [ "$LINE_COUNT2" = "2" ]; then
    echo "Test 4 PASSED: unknown event ignored"
else
    echo "Test 4 FAILED: expected 2 lines, got $LINE_COUNT2"
    exit 1
fi

rm -f "$LOGFILE"
echo "All hook tests passed!"
