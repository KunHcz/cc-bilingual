"""Chinese TUI companion for Claude Code.

Watches CC's own conversation JSONL file for new messages.
No hooks, no settings modification needed.
"""

import glob
import json
import os
import readline  # enables proper line editing (backspace, arrows) for CJK
import subprocess
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cc_translate import translate, translate_mixed, is_short_command

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
CONV_DIR = os.environ.get("CC_CONV_DIR", "")
EXISTING_FILES_PATH = os.environ.get("CC_EXISTING_FILES", "/tmp/cc-bilingual-existing.txt")
TMUX_TARGET = os.environ.get("CC_TMUX_TARGET", "cc-bilingual:0.0")

# ANSI
C = "\033[36m"     # cyan
Y = "\033[33m"     # yellow
G = "\033[32m"     # green
D = "\033[2m"      # dim
B = "\033[1m"      # bold
R = "\033[0m"      # reset
LINE = f"{D}{'─' * 50}{R}"

# State
_recent_sends = []
_first_message = True
_session_ready = False


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
# Session discovery
# ---------------------------------------------------------------------------
def _load_existing_files():
    existing = set()
    if os.path.exists(EXISTING_FILES_PATH):
        with open(EXISTING_FILES_PATH) as f:
            existing = {line.strip() for line in f if line.strip()}
    return existing


def find_session_file(conv_dir, existing_files=None):
    """Wait for a JSONL file that didn't exist before CC started."""
    if existing_files is None:
        existing_files = _load_existing_files()
    while True:
        files = glob.glob(os.path.join(conv_dir, "*.jsonl"))
        for f in sorted(files, key=os.path.getmtime, reverse=True):
            if f not in existing_files:
                return f
        time.sleep(0.5)


# ---------------------------------------------------------------------------
# Conversation watcher
# ---------------------------------------------------------------------------
def watch_conversation(filepath, callback):
    """Tail-watch CC's conversation JSONL for new messages."""
    with open(filepath, "r", encoding="utf-8") as fh:
        fh.seek(0, 2)
        while True:
            line = fh.readline()
            if not line:
                time.sleep(0.3)
                continue
            line = line.strip()
            if not line:
                continue
            try:
                callback(json.loads(line))
            except json.JSONDecodeError:
                pass


def on_entry(entry):
    """Handle a new JSONL entry from CC's conversation log."""
    entry_type = entry.get("type", "")

    if entry_type == "user":
        msg = entry.get("message", {})
        content = msg.get("content", "")
        if isinstance(content, str):
            text = content
        elif isinstance(content, list):
            text = " ".join(c.get("text", "") for c in content if c.get("type") == "text")
        else:
            return
        if not text or should_skip_user(text):
            return
        # User typed directly in CC pane — show both
        zh = translate(text, "en", "zh-CN")
        print(f"\n{Y}You:{R} {text}")
        print(f"{D}     {zh}{R}", flush=True)

    elif entry_type == "assistant":
        msg = entry.get("message", {})
        content = msg.get("content", [])
        if not isinstance(content, list):
            return
        texts = [c["text"] for c in content if c.get("type") == "text" and c.get("text", "").strip()]
        if not texts:
            return
        en_text = "\n".join(texts)
        zh_text = translate_mixed(en_text, "en", "zh-CN")
        # Show both English and Chinese for learning
        print(f"\n{C}{B}CC (EN):{R}\n{en_text}")
        print(f"\n{G}{B}CC (中文):{R}\n{zh_text}")
        print(LINE, flush=True)


# ---------------------------------------------------------------------------
# tmux interaction
# ---------------------------------------------------------------------------
def send_to_cc(text):
    subprocess.run(["tmux", "send-keys", "-t", TMUX_TARGET, "-l", text], capture_output=True)
    subprocess.run(["tmux", "send-keys", "-t", TMUX_TARGET, "Enter"], capture_output=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    global _first_message, _session_ready

    print(f"""
{B}{C}cc-bilingual{R} — Claude Code bilingual companion
{LINE}
{D}  输入中文 → 自动翻译为英文发给 CC
  CC 英文回复 → 同时显示英文原文 + 中文翻译
  短指令 (y/n) 直接透传 | /quit 退出{R}
{LINE}
""", flush=True)

    if not CONV_DIR:
        print(f"{Y}Error: CC_CONV_DIR not set{R}")
        return

    def find_and_watch():
        global _session_ready
        session_file = find_session_file(CONV_DIR)
        sid = os.path.basename(session_file)[:8]
        print(f"{D}  ✓ CC session connected ({sid}...){R}\n", flush=True)
        _session_ready = True
        watch_conversation(session_file, on_entry)

    threading.Thread(target=find_and_watch, daemon=True).start()

    while True:
        try:
            prompt = f"\001{Y}\002输入> \001{R}\002"
            text = input(prompt)
        except (EOFError, KeyboardInterrupt):
            print(f"\n{D}bye{R}")
            break

        stripped = text.strip()
        if not stripped:
            send_to_cc("")
            continue
        if stripped == "/quit":
            break

        if is_short_command(stripped):
            print(f"{D}  → (pass-through) {stripped}{R}", flush=True)
            send_to_cc(stripped)
            continue

        # Translate zh → en
        translated = translate(stripped, "zh-CN", "en")

        if _first_message:
            to_send = translated + "\n\n(Please always respond in English.)"
            _first_message = False
        else:
            to_send = translated

        print(f"{D}  → {translated}{R}", flush=True)
        record_sent(to_send)
        send_to_cc(to_send)


if __name__ == "__main__":
    main()
