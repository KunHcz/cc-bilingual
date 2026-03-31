# cc-bilingual

A bilingual companion for [Claude Code](https://github.com/anthropics/claude-code). Type in Chinese, get English translations sent to Claude Code. See Claude's English responses with Chinese translations side by side.

Built for developers who want to **learn technical English** while using Claude Code.

```
┌─── Claude Code (English) ─────┐┌─── cc-bilingual (中文) ────────┐
│                                ││                                │
│ ❯ Help me write a quicksort   ││ 输入> 帮我写一个快速排序        │
│                                ││   → Help me write a quicksort  │
│ ● Sure, here's a quicksort    ││                                │
│   implementation:              ││ CC (EN):                       │
│                                ││ Sure, here's a quicksort       │
│   ```python                    ││ implementation:                │
│   def quicksort(arr):          ││ ```python                      │
│       ...                      ││ def quicksort(arr):            │
│   ```                          ││ ```                            │
│                                ││                                │
│                                ││ CC (中文):                     │
│                                ││ 当然，这是一个快速排序的实现：  │
│                                ││ ```python                      │
│                                ││ def quicksort(arr):            │
│                                ││ ```                            │
│                                ││ ─────────────────────────────  │
└────────────────────────────────┘└────────────────────────────────┘
```

## Features

- **Zero configuration** — no hooks, no settings changes, no API keys
- **Non-invasive** — reads Claude Code's own conversation logs, doesn't modify anything
- **Bilingual display** — CC responses shown in both English (original) and Chinese (translated)
- **Code-aware** — code blocks are never translated, only natural language
- **Smart pass-through** — short commands (`y`, `n`, `/help`) go directly to CC without translation
- **Both panes interactive** — click or keyboard to switch between CC and TUI

## Requirements

- [Claude Code](https://github.com/anthropics/claude-code) (the `claude` CLI)
- Python 3.8+
- tmux (`brew install tmux`)

## Install

```bash
git clone https://github.com/user/cc-bilingual.git
cd cc-bilingual
chmod +x cc-bilingual.sh
```

## Usage

```bash
# Start in current directory
./cc-bilingual.sh

# Start with a specific project directory
./cc-bilingual.sh ~/my-project
```

This opens a tmux session with two panes:
- **Left**: Claude Code running normally (English)
- **Right**: Chinese TUI companion

### In the TUI (right pane)

| Input | Action |
|-------|--------|
| Chinese text | Translated to English → sent to CC |
| `y`, `n`, numbers | Passed through directly (no translation) |
| `/quit` | Exit the TUI |

### Switching panes

- **Mouse click** on the pane you want
- **Ctrl-B** then **arrow key** (left/right)

## How it works

```
You type Chinese ──→ Google Translate ──→ English text ──→ CC
                                                          │
CC responds in English ←──────────────────────────────────┘
         │
         ├──→ Show English original in TUI
         └──→ Google Translate ──→ Show Chinese translation in TUI
```

No hooks or config changes. The TUI watches Claude Code's own conversation log files at `~/.claude/projects/` for new messages.

Translation is handled by Google Translate's public API — no API key needed, no rate limits for normal usage.

## Tech stack

- **Python 3** (stdlib only, zero external dependencies)
- **tmux** (dual-pane layout)
- **Google Translate API** (unofficial, free, no key)

## License

MIT
