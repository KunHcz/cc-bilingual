"""Chinese TUI companion window for cc-bilingual.

Runs in the right tmux pane. Accepts Chinese input, translates to English,
and injects into the CC pane. Watches a JSONL log file for new entries and
translates them from English to Chinese for display.
"""

import json
import os
import readline  # enables proper line editing (backspace, arrow keys) for input()
import subprocess
import sys
import threading
import time

from cc_translate import translate, translate_mixed, is_short_command

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

LOG_PATH = os.environ.get("CC_BILINGUAL_LOG", "/tmp/cc-bilingual.jsonl")
TMUX_TARGET = os.environ.get("CC_TMUX_TARGET", "cc-bilingual:0.0")

# ---------------------------------------------------------------------------
# Color constants
# ---------------------------------------------------------------------------

CYAN = "\033[36m"
YELLOW = "\033[33m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"
CLEAR_LINE = "\033[2K\r"

# ---------------------------------------------------------------------------
# Dedup state
# ---------------------------------------------------------------------------

_recent_sends: list = []
_DEDUP_MAX = 20
_DEDUP_TTL = 5  # seconds


def record_sent(text: str) -> None:
    """Record a translated message that was sent to CC."""
    _recent_sends.append((time.time(), text.strip()))
    if len(_recent_sends) > _DEDUP_MAX:
        del _recent_sends[:-_DEDUP_MAX]


def should_skip_user_message(text: str) -> bool:
    """Return True if this user message is an echo of something we just sent."""
    stripped = text.strip()
    now = time.time()
    for ts, sent in _recent_sends:
        if now - ts <= _DEDUP_TTL and sent == stripped:
            return True
    return False


# ---------------------------------------------------------------------------
# Log watcher
# ---------------------------------------------------------------------------

def watch_logfile(logpath: str, callback) -> None:
    """Watch *logpath* for new JSONL lines and call callback(data) for each.

    Seeks to the end of the file on open so only NEW lines are processed.
    Polls for file existence and new content every 0.3 s.
    Designed to run as a daemon thread.
    """
    # Wait for file to exist
    while not os.path.exists(logpath):
        time.sleep(0.3)

    with open(logpath, "r", encoding="utf-8") as fh:
        # Seek to end — ignore pre-existing lines
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
                data = json.loads(line)
                callback(data)
            except json.JSONDecodeError:
                pass


# ---------------------------------------------------------------------------
# Send to CC pane
# ---------------------------------------------------------------------------

def send_to_cc(text: str) -> None:
    """Send *text* as literal keystrokes followed by Enter to the CC tmux pane."""
    subprocess.run(
        ["tmux", "send-keys", "-t", TMUX_TARGET, "-l", text],
        capture_output=True,
    )
    subprocess.run(
        ["tmux", "send-keys", "-t", TMUX_TARGET, "Enter"],
        capture_output=True,
    )


# ---------------------------------------------------------------------------
# Message display
# ---------------------------------------------------------------------------

def on_message(data: dict) -> None:
    """Handle a log entry from the CC hook."""
    role = data.get("role", "")
    text = data.get("text", "")
    if not text:
        return

    if role == "user":
        if should_skip_user_message(text):
            return
        translated = translate(text, "en", "zh-CN")
        print(
            f"\n{YELLOW}你 (CC):{RESET} {translated}\n"
            f"  {DIM}EN: {text}{RESET}",
            flush=True,
        )

    elif role == "assistant":
        translated = translate_mixed(text, "en", "zh-CN")
        print(
            f"\n{CYAN}CC:{RESET} {translated}\n"
            f"{DIM}{'─' * 50}{RESET}",
            flush=True,
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print(
        f"\n{BOLD}{CYAN}cc-bilingual TUI{RESET}\n"
        f"{DIM}中文输入 → 英文 → CC pane | CC 输出 → 中文显示{RESET}\n"
        f"{DIM}输入 /quit 退出{RESET}\n",
        flush=True,
    )

    watcher_thread = threading.Thread(
        target=watch_logfile,
        args=(LOG_PATH, on_message),
        daemon=True,
    )
    watcher_thread.start()

    while True:
        try:
            # \001 \002 wrap non-printable chars so readline calculates cursor correctly
            prompt = f"\001{YELLOW}\002输入> \001{RESET}\002"
            text = input(prompt)
        except (EOFError, KeyboardInterrupt):
            print(f"\n{DIM}再见{RESET}")
            break

        if not text.strip():
            # Send an empty Enter to CC (e.g. to confirm a prompt)
            send_to_cc("")
            continue

        if text.strip() == "/quit":
            print(f"{DIM}退出{RESET}")
            break

        if is_short_command(text):
            print(f"{DIM}(透传) {text}{RESET}", flush=True)
            send_to_cc(text)
            continue

        # Translate Chinese → English, then send
        translated = translate(text, "zh-CN", "en")
        print(f"{DIM}EN: {translated}{RESET}", flush=True)
        record_sent(translated)
        send_to_cc(translated)


if __name__ == "__main__":
    main()
