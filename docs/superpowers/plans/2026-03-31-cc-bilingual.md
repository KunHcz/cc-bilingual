# CC Bilingual Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a tmux-based bilingual companion for Claude Code - user types Chinese in a companion TUI, it translates to English and injects into CC; CC's English responses are translated back to Chinese. Both windows visible for language learning.

**Architecture:** Startup script creates a tmux session with two panes. Left pane runs `claude` normally. Right pane runs a Python TUI. CC hooks (UserPromptSubmit + Stop) capture conversation events and append to a JSONL log file. The TUI tail-watches this file, translates English to Chinese via Lingva API, and displays. User Chinese input is translated to English and injected via `tmux send-keys`.

**Tech Stack:** Python 3 (stdlib only, zero external deps), tmux, Lingva Translate API (`lingva.ml`), CC hooks

---

## File Structure

```
~/cc-bilingual/
├── cc-bilingual.sh          # Entry point: tmux setup + hook injection + cleanup
├── cc_translate.py           # Translation functions (Lingva API + code block handling)
├── cc_tui.py                 # Chinese TUI: input loop + log watcher + display
├── cc_hook.sh                # CC hook script: extract text from hook JSON → append JSONL
└── tests/
    └── test_translate.py     # Unit tests for translation logic
```

---

### Task 0: Prerequisites

- [ ] **Step 1: Install tmux**

```bash
brew install tmux
```

Expected: `tmux` command available.

- [ ] **Step 2: Verify Lingva API is reachable**

```bash
curl -s "https://lingva.ml/api/v1/en/zh/hello" | python3 -c "import sys,json; print(json.load(sys.stdin)['translation'])"
```

Expected: prints `你好`

- [ ] **Step 3: Init git repo**

```bash
cd ~/cc-bilingual
git init
echo "__pycache__/" > .gitignore
echo "*.pyc" >> .gitignore
git add .gitignore
git commit -m "init: project skeleton"
```

---

### Task 1: Translation Core (`cc_translate.py`)

**Files:**
- Create: `~/cc-bilingual/cc_translate.py`
- Create: `~/cc-bilingual/tests/test_translate.py`

- [ ] **Step 1: Write failing tests for `split_code_blocks`**

```python
# tests/test_translate.py
import unittest

class TestSplitCodeBlocks(unittest.TestCase):

    def test_no_code(self):
        from cc_translate import split_code_blocks
        result = split_code_blocks("Hello world")
        self.assertEqual(result, [("text", "Hello world")])

    def test_only_code(self):
        from cc_translate import split_code_blocks
        code = "```python\nprint('hi')\n```"
        result = split_code_blocks(code)
        self.assertEqual(result, [("code", code)])

    def test_mixed(self):
        from cc_translate import split_code_blocks
        text = "Here is code:\n```python\nprint('hi')\n```\nDone."
        result = split_code_blocks(text)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0][0], "text")
        self.assertEqual(result[1][0], "code")
        self.assertEqual(result[2][0], "text")
        self.assertIn("Here is code:", result[0][1])
        self.assertIn("print('hi')", result[1][1])
        self.assertIn("Done.", result[2][1])

    def test_multiple_code_blocks(self):
        from cc_translate import split_code_blocks
        text = "First:\n```js\na()\n```\nMiddle\n```py\nb()\n```\nEnd"
        result = split_code_blocks(text)
        types = [t for t, _ in result]
        self.assertEqual(types, ["text", "code", "text", "code", "text"])

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd ~/cc-bilingual && python3 -m pytest tests/test_translate.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'cc_translate'`

- [ ] **Step 3: Implement `split_code_blocks`**

```python
# cc_translate.py
"""Translation utilities for cc-bilingual."""

import json
import os
import re
import urllib.parse
import urllib.request

LINGVA_BASE = os.environ.get("CC_LINGVA_URL", "https://lingva.ml")


def split_code_blocks(text):
    """Split text into (type, content) segments. type='code' for ```...``` blocks."""
    pattern = r'(```[^\n]*\n[\s\S]*?```)'
    parts = re.split(pattern, text)
    result = []
    for part in parts:
        if not part:
            continue
        if re.match(r'^```', part):
            result.append(('code', part))
        else:
            result.append(('text', part))
    return result
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd ~/cc-bilingual && python3 -m pytest tests/test_translate.py::TestSplitCodeBlocks -v
```

Expected: 4 passed

- [ ] **Step 5: Add failing tests for `is_short_command`**

Append to `tests/test_translate.py`:

```python
class TestIsShortCommand(unittest.TestCase):

    def test_single_char(self):
        from cc_translate import is_short_command
        self.assertTrue(is_short_command("y"))
        self.assertTrue(is_short_command("n"))

    def test_short_ascii(self):
        from cc_translate import is_short_command
        self.assertTrue(is_short_command("yes"))
        self.assertTrue(is_short_command("no"))

    def test_slash_commands(self):
        from cc_translate import is_short_command
        self.assertTrue(is_short_command("/quit"))
        self.assertTrue(is_short_command("/help"))

    def test_chinese_not_short(self):
        from cc_translate import is_short_command
        self.assertFalse(is_short_command("你好"))
        self.assertFalse(is_short_command("帮我写代码"))

    def test_long_english_not_short(self):
        from cc_translate import is_short_command
        self.assertFalse(is_short_command("help me write code"))

    def test_empty_and_whitespace(self):
        from cc_translate import is_short_command
        self.assertTrue(is_short_command(""))
        self.assertTrue(is_short_command("   "))
```

- [ ] **Step 6: Implement `is_short_command`**

Append to `cc_translate.py`:

```python
def is_short_command(text):
    """Return True if text should be passed through without translation."""
    stripped = text.strip()
    if not stripped:
        return True
    if len(stripped) <= 3 and stripped.isascii():
        return True
    if stripped.lower() in ('yes', 'no', 'exit', 'quit', 'help', 'clear'):
        return True
    if stripped.startswith('/'):
        return True
    return False
```

- [ ] **Step 7: Run to verify pass**

```bash
cd ~/cc-bilingual && python3 -m pytest tests/test_translate.py -v
```

Expected: all passed

- [ ] **Step 8: Add failing tests for `translate` (mocked HTTP)**

Append to `tests/test_translate.py`:

```python
from unittest.mock import patch, MagicMock
import json as _json

class TestTranslate(unittest.TestCase):

    def _mock_response(self, translation_text):
        mock_resp = MagicMock()
        mock_resp.read.return_value = _json.dumps({"translation": translation_text}).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        return mock_resp

    @patch("cc_translate.urllib.request.urlopen")
    def test_basic_translation(self, mock_urlopen):
        from cc_translate import translate
        mock_urlopen.return_value = self._mock_response("你好世界")
        result = translate("Hello World", "en", "zh")
        self.assertEqual(result, "你好世界")

    @patch("cc_translate.urllib.request.urlopen")
    def test_empty_text(self, mock_urlopen):
        from cc_translate import translate
        result = translate("", "en", "zh")
        self.assertEqual(result, "")
        mock_urlopen.assert_not_called()

    @patch("cc_translate.urllib.request.urlopen")
    def test_api_failure_returns_original(self, mock_urlopen):
        from cc_translate import translate
        mock_urlopen.side_effect = Exception("Network error")
        result = translate("Hello", "en", "zh")
        self.assertEqual(result, "Hello")

    @patch("cc_translate.urllib.request.urlopen")
    def test_long_text_chunked(self, mock_urlopen):
        from cc_translate import translate
        mock_urlopen.return_value = self._mock_response("翻译结果")
        long_text = "Short paragraph one.\n\nShort paragraph two."
        # Under 500 chars, no chunking
        result = translate(long_text, "en", "zh")
        self.assertEqual(mock_urlopen.call_count, 1)

    @patch("cc_translate.urllib.request.urlopen")
    def test_long_text_splits_by_paragraph(self, mock_urlopen):
        from cc_translate import translate
        mock_urlopen.return_value = self._mock_response("翻译")
        para = "A" * 300
        long_text = f"{para}\n\n{para}"  # 600+ chars total
        result = translate(long_text, "en", "zh")
        self.assertEqual(mock_urlopen.call_count, 2)
```

- [ ] **Step 9: Implement `translate` with chunking**

Append to `cc_translate.py`:

```python
def _translate_single(text, source, target):
    """Translate a single chunk via Lingva API. Returns original on failure."""
    try:
        encoded = urllib.parse.quote(text.strip())
        url = f"{LINGVA_BASE}/api/v1/{source}/{target}/{encoded}"
        req = urllib.request.Request(url, headers={"User-Agent": "cc-bilingual/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            return data.get("translation", text)
    except Exception:
        return text


def translate(text, source="en", target="zh"):
    """Translate text using Lingva API. Auto-chunks long texts by paragraph."""
    text = text.strip()
    if not text:
        return text
    if len(text) > 500:
        paragraphs = text.split('\n\n')
        translated = [_translate_single(p, source, target) if p.strip() else '' for p in paragraphs]
        return '\n\n'.join(translated)
    return _translate_single(text, source, target)
```

- [ ] **Step 10: Run to verify pass**

```bash
cd ~/cc-bilingual && python3 -m pytest tests/test_translate.py -v
```

Expected: all passed

- [ ] **Step 11: Add failing tests for `translate_mixed`**

Append to `tests/test_translate.py`:

```python
class TestTranslateMixed(unittest.TestCase):

    @patch("cc_translate.urllib.request.urlopen")
    def test_text_only(self, mock_urlopen):
        from cc_translate import translate_mixed
        mock_resp = MagicMock()
        mock_resp.read.return_value = _json.dumps({"translation": "你好"}).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = translate_mixed("Hello", "en", "zh")
        self.assertEqual(result, "你好")

    @patch("cc_translate._translate_single")
    def test_code_blocks_preserved(self, mock_translate):
        from cc_translate import translate_mixed
        mock_translate.return_value = "翻译文本"

        text = "Explanation:\n```python\nprint('hi')\n```\nDone."
        result = translate_mixed(text, "en", "zh")
        self.assertIn("```python\nprint('hi')\n```", result)
        self.assertIn("翻译文本", result)

    @patch("cc_translate._translate_single")
    def test_only_code_no_translation(self, mock_translate):
        from cc_translate import translate_mixed
        code = "```python\nprint('hi')\n```"
        result = translate_mixed(code, "en", "zh")
        self.assertEqual(result, code)
        mock_translate.assert_not_called()
```

- [ ] **Step 12: Implement `translate_mixed`**

Append to `cc_translate.py`:

```python
def translate_mixed(text, source="en", target="zh"):
    """Translate text parts only, keep code blocks unchanged."""
    segments = split_code_blocks(text)
    if not segments:
        return text
    parts = []
    for seg_type, content in segments:
        if seg_type == 'code':
            parts.append(content)
        else:
            if content.strip():
                parts.append(translate(content, source, target))
            else:
                parts.append(content)
    return ''.join(parts)
```

- [ ] **Step 13: Run full test suite**

```bash
cd ~/cc-bilingual && python3 -m pytest tests/test_translate.py -v
```

Expected: all passed

- [ ] **Step 14: Commit**

```bash
cd ~/cc-bilingual
git add cc_translate.py tests/test_translate.py
git commit -m "feat: translation core with code block handling and chunking"
```

---

### Task 2: Hook Script (`cc_hook.sh`)

**Files:**
- Create: `~/cc-bilingual/cc_hook.sh`
- Create: `~/cc-bilingual/tests/test_hook.sh`

- [ ] **Step 1: Write hook test script**

```bash
# tests/test_hook.sh
#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
HOOK="$SCRIPT_DIR/cc_hook.sh"
LOGFILE="/tmp/cc-bilingual-test.jsonl"

# Clean
rm -f "$LOGFILE"
touch "$LOGFILE"

# Test 1: UserPromptSubmit event
echo '{"prompt": "Help me write a sort", "session_id": "test123"}' | \
    CC_BILINGUAL_LOG="$LOGFILE" bash "$HOOK" user

RESULT=$(cat "$LOGFILE")
echo "Test 1 result: $RESULT"
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
echo "Test 2 result: $RESULT"
echo "$RESULT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
assert data['role'] == 'assistant', f'Expected assistant, got {data[\"role\"]}'
assert 'quicksort' in data['text'], f'Wrong text: {data[\"text\"]}'
print('Test 2 PASSED: assistant event')
"

# Test 3: Empty prompt
echo '{"prompt": "", "session_id": "test123"}' | \
    CC_BILINGUAL_LOG="$LOGFILE" bash "$HOOK" user

LINE_COUNT=$(wc -l < "$LOGFILE" | tr -d ' ')
if [ "$LINE_COUNT" = "2" ]; then
    echo "Test 3 PASSED: empty prompt ignored"
else
    echo "Test 3 FAILED: expected 2 lines, got $LINE_COUNT"
    exit 1
fi

# Cleanup
rm -f "$LOGFILE"
echo "All hook tests passed!"
```

- [ ] **Step 2: Run to verify it fails**

```bash
cd ~/cc-bilingual && bash tests/test_hook.sh
```

Expected: FAIL because `cc_hook.sh` doesn't exist

- [ ] **Step 3: Implement `cc_hook.sh`**

```bash
#!/bin/bash
# CC Bilingual Hook - extracts text from CC hook events, appends to JSONL log.
# Usage: cat | cc_hook.sh <user|assistant>
# Reads hook JSON from stdin, writes {"role": "...", "text": "..."} to log.

LOGFILE="${CC_BILINGUAL_LOG:-/tmp/cc-bilingual.jsonl}"
EVENT_TYPE="$1"

INPUT=$(cat)

case "$EVENT_TYPE" in
    user)
        FIELD="prompt"
        ROLE="user"
        ;;
    assistant)
        FIELD="response_text"
        ROLE="assistant"
        ;;
    *)
        exit 0
        ;;
esac

# Extract field and write JSON line
python3 -c "
import sys, json

data = json.loads(sys.argv[1])
text = data.get(sys.argv[2], '').strip()
role = sys.argv[3]

if text:
    line = json.dumps({'role': role, 'text': text}, ensure_ascii=False)
    with open(sys.argv[4], 'a') as f:
        f.write(line + '\n')
" "$INPUT" "$FIELD" "$ROLE" "$LOGFILE"
```

- [ ] **Step 4: Make executable and run tests**

```bash
chmod +x ~/cc-bilingual/cc_hook.sh
cd ~/cc-bilingual && bash tests/test_hook.sh
```

Expected: "All hook tests passed!"

- [ ] **Step 5: Commit**

```bash
cd ~/cc-bilingual
git add cc_hook.sh tests/test_hook.sh
git commit -m "feat: hook script for capturing CC conversation events"
```

---

### Task 3: Chinese TUI (`cc_tui.py`)

**Files:**
- Create: `~/cc-bilingual/cc_tui.py`
- Create: `~/cc-bilingual/tests/test_tui.py`

- [ ] **Step 1: Write failing tests for TUI helper logic**

```python
# tests/test_tui.py
import unittest
import json
import os
import tempfile
import time
import threading


class TestLogWatcher(unittest.TestCase):

    def test_reads_new_lines(self):
        from cc_tui import watch_logfile
        received = []

        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            logpath = f.name
            # Write initial line before watcher starts
            f.write(json.dumps({"role": "assistant", "text": "hello"}) + "\n")
            f.flush()

        try:
            # Start watcher at end of file
            t = threading.Thread(
                target=watch_logfile,
                args=(logpath, lambda d: received.append(d)),
                daemon=True
            )
            t.start()
            time.sleep(0.5)

            # Write a new line
            with open(logpath, 'a') as f:
                f.write(json.dumps({"role": "assistant", "text": "new"}) + "\n")

            time.sleep(1)
            # Should have picked up "new" but not "hello" (started at EOF)
            texts = [d["text"] for d in received]
            self.assertIn("new", texts)
        finally:
            os.unlink(logpath)


class TestDedup(unittest.TestCase):

    def test_recent_send_is_skipped(self):
        from cc_tui import should_skip_user_message, record_sent
        record_sent("Hello World")
        self.assertTrue(should_skip_user_message("Hello World"))

    def test_old_send_not_skipped(self):
        from cc_tui import should_skip_user_message, _recent_sends
        _recent_sends.clear()
        _recent_sends.append((time.time() - 10, "Old message"))
        self.assertFalse(should_skip_user_message("Old message"))

    def test_different_text_not_skipped(self):
        from cc_tui import should_skip_user_message, record_sent
        record_sent("Hello")
        self.assertFalse(should_skip_user_message("Goodbye"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify they fail**

```bash
cd ~/cc-bilingual && python3 -m pytest tests/test_tui.py -v
```

Expected: FAIL

- [ ] **Step 3: Implement `cc_tui.py`**

```python
#!/usr/bin/env python3
"""Chinese TUI companion for Claude Code."""

import json
import os
import subprocess
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cc_translate import is_short_command, translate, translate_mixed

LOGFILE = os.environ.get("CC_BILINGUAL_LOG", "/tmp/cc-bilingual.jsonl")
TMUX_TARGET = os.environ.get("CC_TMUX_TARGET", "cc-bilingual:0.0")

# Colors
CYAN = "\033[36m"
YELLOW = "\033[33m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"
CLEAR_LINE = "\033[2K\r"

# Dedup: track messages sent from TUI
_recent_sends = []


def record_sent(text):
    """Record a sent message for dedup."""
    _recent_sends.append((time.time(), text.strip()))
    if len(_recent_sends) > 20:
        _recent_sends.pop(0)


def should_skip_user_message(text):
    """Return True if this user message was recently sent from TUI."""
    now = time.time()
    for sent_time, sent_text in _recent_sends:
        if now - sent_time < 5 and sent_text == text.strip():
            return True
    return False


def watch_logfile(logpath, callback):
    """Tail-watch a JSONL file, calling callback(data) for each new line."""
    while not os.path.exists(logpath):
        time.sleep(0.3)
    with open(logpath, 'r') as f:
        f.seek(0, 2)  # start at end
        while True:
            line = f.readline()
            if line:
                line = line.strip()
                if line:
                    try:
                        callback(json.loads(line))
                    except json.JSONDecodeError:
                        pass
            else:
                time.sleep(0.3)


def send_to_cc(text):
    """Inject text into CC tmux pane."""
    subprocess.run(["tmux", "send-keys", "-t", TMUX_TARGET, "-l", text],
                   capture_output=True)
    subprocess.run(["tmux", "send-keys", "-t", TMUX_TARGET, "Enter"],
                   capture_output=True)


def on_message(data):
    """Handle hook message: translate and display."""
    role = data.get("role", "")
    text = data.get("text", "")
    if not text:
        return

    if role == "user":
        if should_skip_user_message(text):
            return
        # User typed directly in CC window - translate for Chinese display
        translated = translate(text, "en", "zh")
        print(f"\n{YELLOW}你 (CC):{RESET} {translated}")
        print(f"  {DIM}EN: {text}{RESET}")

    elif role == "assistant":
        print(f"\n{DIM}[翻译中...]{RESET}", end="", flush=True)
        translated = translate_mixed(text, "en", "zh")
        print(f"{CLEAR_LINE}{CYAN}CC:{RESET} {translated}")
        print(f"{DIM}{'─' * 50}{RESET}")


def main():
    print(f"\n{BOLD}  CC 双语学习模式{RESET}")
    print(f"  在此输入中文，自动翻译后发送给 CC")
    print(f"  y/n 等短指令直接透传 | /quit 退出")
    print(f"{DIM}{'─' * 50}{RESET}\n")

    watcher = threading.Thread(target=watch_logfile, args=(LOGFILE, on_message), daemon=True)
    watcher.start()

    while True:
        try:
            user_input = input(f"{YELLOW}输入> {RESET}")
            stripped = user_input.strip()

            if not stripped:
                send_to_cc("")
                continue

            if stripped == "/quit":
                break

            if is_short_command(stripped):
                send_to_cc(stripped)
                print(f"  {DIM}(透传) {stripped}{RESET}")
            else:
                print(f"  {DIM}[翻译中...]{RESET}", end="", flush=True)
                translated = translate(stripped, "zh", "en")
                print(f"{CLEAR_LINE}  {DIM}EN: {translated}{RESET}")
                record_sent(translated)
                send_to_cc(translated)

        except (EOFError, KeyboardInterrupt):
            print()
            break


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests**

```bash
cd ~/cc-bilingual && python3 -m pytest tests/test_tui.py -v
```

Expected: all passed

- [ ] **Step 5: Commit**

```bash
cd ~/cc-bilingual
git add cc_tui.py tests/test_tui.py
git commit -m "feat: Chinese TUI with log watcher and tmux injection"
```

---

### Task 4: Startup Script (`cc-bilingual.sh`)

**Files:**
- Create: `~/cc-bilingual/cc-bilingual.sh`

- [ ] **Step 1: Implement startup script**

```bash
#!/bin/bash
# CC Bilingual - Launch Claude Code with Chinese translation companion.
# Usage: ./cc-bilingual.sh [claude args...]

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
    # Restore original settings
    if [ -f "$BACKUP_FILE" ]; then
        cp "$BACKUP_FILE" "$SETTINGS_FILE"
        rm -f "$BACKUP_FILE"
    fi
    rm -f "$LOGFILE"
    # Don't kill session here - let tmux handle it naturally
}
trap cleanup EXIT INT TERM

# --- Reset log ---
: > "$LOGFILE"

# --- Inject hooks ---
mkdir -p "$(dirname "$SETTINGS_FILE")"
[ ! -f "$SETTINGS_FILE" ] && echo '{}' > "$SETTINGS_FILE"
cp "$SETTINGS_FILE" "$BACKUP_FILE"

python3 -c "
import json, sys

path, hook_cmd = sys.argv[1], sys.argv[2]

with open(path) as f:
    cfg = json.load(f)

cfg.setdefault('hooks', {})

user_hook = {'hooks': [{'type': 'command', 'command': f'cat | {hook_cmd} user', 'timeout': 5}]}
stop_hook = {'hooks': [{'type': 'command', 'command': f'cat | {hook_cmd} assistant', 'timeout': 30}]}

cfg['hooks'].setdefault('UserPromptSubmit', []).append(user_hook)
cfg['hooks'].setdefault('Stop', []).append(stop_hook)

with open(path, 'w') as f:
    json.dump(cfg, f, indent=2)
" "$SETTINGS_FILE" "$HOOK_SCRIPT"

# --- Kill existing session if any ---
tmux kill-session -t "$SESSION_NAME" 2>/dev/null || true

# --- Create tmux session ---
tmux new-session -d -s "$SESSION_NAME"
tmux split-window -h -t "$SESSION_NAME"

# Right pane (1): TUI
tmux send-keys -t "$SESSION_NAME:0.1" \
    "CC_BILINGUAL_LOG='$LOGFILE' CC_TMUX_TARGET='$SESSION_NAME:0.0' python3 '$TUI_SCRIPT'" Enter

# Left pane (0): Claude Code
CLAUDE_ARGS="${*}"
tmux send-keys -t "$SESSION_NAME:0.0" "claude $CLAUDE_ARGS" Enter

# Focus right pane (Chinese input)
tmux select-pane -t "$SESSION_NAME:0.1"

# Attach
tmux attach-session -t "$SESSION_NAME"
```

- [ ] **Step 2: Make executable**

```bash
chmod +x ~/cc-bilingual/cc-bilingual.sh
```

- [ ] **Step 3: Test dependency check (dry run)**

```bash
cd ~/cc-bilingual && bash -c 'SESSION_NAME=test-check; for cmd in tmux python3 claude; do command -v "$cmd" &>/dev/null && echo "$cmd: OK" || echo "$cmd: MISSING"; done'
```

Expected: shows which deps are available

- [ ] **Step 4: Test hook injection/restore**

```bash
cd ~/cc-bilingual

# Save current settings
ORIG=$(cat ~/.claude/settings.json 2>/dev/null || echo '{}')

# Run injection
python3 -c "
import json, sys
path, hook_cmd = sys.argv[1], sys.argv[2]
with open(path) as f:
    cfg = json.load(f)
cfg.setdefault('hooks', {})
cfg['hooks'].setdefault('UserPromptSubmit', []).append({'hooks': [{'type': 'command', 'command': f'cat | {hook_cmd} user'}]})
cfg['hooks'].setdefault('Stop', []).append({'hooks': [{'type': 'command', 'command': f'cat | {hook_cmd} assistant'}]})
with open(path, 'w') as f:
    json.dump(cfg, f, indent=2)
" ~/.claude/settings.json ~/cc-bilingual/cc_hook.sh

# Verify hooks were added
python3 -c "
import json
with open('$HOME/.claude/settings.json') as f:
    cfg = json.load(f)
assert 'UserPromptSubmit' in cfg.get('hooks', {}), 'Missing UserPromptSubmit'
assert 'Stop' in cfg.get('hooks', {}), 'Missing Stop'
print('Hook injection: OK')
"

# Restore
echo "$ORIG" > ~/.claude/settings.json
echo "Settings restored: OK"
```

Expected: "Hook injection: OK" + "Settings restored: OK"

- [ ] **Step 5: Commit**

```bash
cd ~/cc-bilingual
git add cc-bilingual.sh
git commit -m "feat: startup script with tmux setup and hook management"
```

---

### Task 5: Integration Test

- [ ] **Step 1: Run full tool**

```bash
cd ~/cc-bilingual && ./cc-bilingual.sh
```

Verify:
1. tmux session opens with two panes
2. Left pane: `claude` starts normally
3. Right pane: Chinese TUI shows welcome message
4. Type Chinese in right pane → see English translation → appears in CC
5. CC responds in English → Chinese translation appears in right pane
6. Code blocks are NOT translated
7. Short commands (y/n) pass through correctly
8. Can also type directly in CC left pane

- [ ] **Step 2: Test cleanup**

Press `Ctrl-B` then `d` to detach from tmux, or `/quit` in TUI.

Verify:
- `~/.claude/settings.json` restored to original (no bilingual hooks left)
- `/tmp/cc-bilingual.jsonl` cleaned up

- [ ] **Step 3: Add convenience alias (optional)**

```bash
echo 'alias ccb="~/cc-bilingual/cc-bilingual.sh"' >> ~/.zshrc
```

- [ ] **Step 4: Final commit**

```bash
cd ~/cc-bilingual
git add -A
git commit -m "feat: cc-bilingual v1.0 - bilingual Claude Code companion"
```
