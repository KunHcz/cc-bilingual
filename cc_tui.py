"""Chinese TUI companion for Claude Code.

Watches CC's own conversation JSONL file for new messages.
No hooks, no settings modification needed.
"""

import glob
import json
import os
import readline  # proper line editing for CJK input
import subprocess
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cc_translate import translate, translate_mixed, is_short_command

# ---------------------------------------------------------------------------
# Config from env
# ---------------------------------------------------------------------------
CONV_DIR = os.environ.get("CC_CONV_DIR", "")
EXISTING_FILES_PATH = os.environ.get("CC_EXISTING_FILES", "/tmp/cc-bilingual-existing.txt")
TMUX_TARGET = os.environ.get("CC_TMUX_TARGET", "cc-bilingual:0.0")

# Colors
CYAN = "\033[36m"
YELLOW = "\033[33m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"

# Dedup
_recent_sends = []
_first_message = True


def record_sent(text):
    _recent_sends.append((time.time(), text.strip()))
    if len(_recent_sends) > 20:
        del _recent_sends[:-20]


def should_skip_user(text):
    now = time.time()
    for ts, sent in _recent_sends:
        if now - ts < 10 and sent == text.strip():
            return True
    return False


# ---------------------------------------------------------------------------
# Find the CC session JSONL
# ---------------------------------------------------------------------------
def _load_existing_files():
    """Load the list of pre-existing JSONL files (recorded before CC started)."""
    existing = set()
    if os.path.exists(EXISTING_FILES_PATH):
        with open(EXISTING_FILES_PATH) as f:
            existing = {line.strip() for line in f if line.strip()}
    return existing


def find_session_file(conv_dir, existing_files=None):
    """Wait for a JSONL file that didn't exist before CC started."""
    if existing_files is None:
        existing_files = _load_existing_files()
    print(f"{DIM}Waiting for CC session...{RESET}", flush=True)
    while True:
        files = glob.glob(os.path.join(conv_dir, "*.jsonl"))
        for f in sorted(files, key=os.path.getmtime, reverse=True):
            if f not in existing_files:
                basename = os.path.basename(f)
                print(f"{DIM}Session: {basename[:12]}...{RESET}\n", flush=True)
                return f
        time.sleep(0.5)


# ---------------------------------------------------------------------------
# Watch CC conversation JSONL
# ---------------------------------------------------------------------------
def watch_conversation(filepath, callback):
    """Tail-watch CC's conversation JSONL for new messages."""
    with open(filepath, "r", encoding="utf-8") as fh:
        fh.seek(0, 2)  # start at end
        while True:
            line = fh.readline()
            if not line:
                time.sleep(0.3)
                continue
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                callback(entry)
            except json.JSONDecodeError:
                pass


def on_entry(entry):
    """Handle a new JSONL entry from CC's conversation log."""
    entry_type = entry.get("type", "")

    if entry_type == "user":
        msg = entry.get("message", {})
        content = msg.get("content", "")
        # Extract text
        if isinstance(content, str):
            text = content
        elif isinstance(content, list):
            text = " ".join(c.get("text", "") for c in content if c.get("type") == "text")
        else:
            return
        if not text or should_skip_user(text):
            return
        # User typed directly in CC pane
        translated = translate(text, "en", "zh-CN")
        print(f"\n{YELLOW}You (CC):{RESET} {text}", flush=True)
        print(f"{DIM}中文: {translated}{RESET}", flush=True)

    elif entry_type == "assistant":
        msg = entry.get("message", {})
        content = msg.get("content", [])
        if not isinstance(content, list):
            return
        # Collect all text blocks
        texts = [c["text"] for c in content if c.get("type") == "text" and c.get("text", "").strip()]
        if not texts:
            return
        full_text = "\n".join(texts)
        translated = translate_mixed(full_text, "en", "zh-CN")
        print(f"\n{CYAN}CC:{RESET} {translated}", flush=True)
        print(f"{DIM}{'─' * 50}{RESET}", flush=True)


# ---------------------------------------------------------------------------
# Send to CC
# ---------------------------------------------------------------------------
def send_to_cc(text):
    subprocess.run(["tmux", "send-keys", "-t", TMUX_TARGET, "-l", text], capture_output=True)
    subprocess.run(["tmux", "send-keys", "-t", TMUX_TARGET, "Enter"], capture_output=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    global _first_message

    print(f"\n{BOLD}{CYAN}cc-bilingual{RESET}")
    print(f"{DIM}中文输入 → 英文发给 CC | CC 英文回复 → 中文翻译{RESET}")
    print(f"{DIM}/quit 退出 | Ctrl-B + 方向键 或鼠标点击切换 pane{RESET}\n", flush=True)

    if not CONV_DIR:
        print(f"{YELLOW}Error: CC_CONV_DIR not set{RESET}")
        return

    # Find the session file (one that didn't exist before)
    session_file = find_session_file(CONV_DIR)

    # Start watcher
    watcher = threading.Thread(target=watch_conversation, args=(session_file, on_entry), daemon=True)
    watcher.start()

    while True:
        try:
            prompt = f"\001{YELLOW}\002输入> \001{RESET}\002"
            text = input(prompt)
        except (EOFError, KeyboardInterrupt):
            print(f"\n{DIM}再见{RESET}")
            break

        stripped = text.strip()
        if not stripped:
            send_to_cc("")
            continue
        if stripped == "/quit":
            break

        if is_short_command(stripped):
            print(f"{DIM}(透传) {stripped}{RESET}", flush=True)
            send_to_cc(stripped)
            continue

        # Translate zh → en
        translated = translate(stripped, "zh-CN", "en")

        # First message: ask CC to respond in English
        if _first_message:
            to_send = translated + "\n\n(Please always respond in English.)"
            _first_message = False
        else:
            to_send = translated

        print(f"{DIM}EN: {translated}{RESET}", flush=True)
        record_sent(to_send)
        send_to_cc(to_send)


if __name__ == "__main__":
    main()
