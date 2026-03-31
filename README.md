<div align="center">

# cc-bilingual

**Claude Code 双语伴侣 — 用中文写代码，用英文学技术**

[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![Zero Dependencies](https://img.shields.io/badge/Dependencies-0-brightgreen?style=flat-square)]()
[![Claude Code](https://img.shields.io/badge/Claude_Code-Compatible-blueviolet?style=flat-square&logo=anthropic)](https://github.com/anthropics/claude-code)

<br>

*一边用 Claude Code 写代码，一边学技术英文。输入中文，自动翻译成英文发给 CC；CC 的英文回复，自动翻译成中文展示。双语对照，沉浸式学习。*

<br>

```
┌─── Claude Code (English) ─────────┐┌─── cc-bilingual (中文) ──────────┐
│                                    ││                                  │
│ ❯ Help me write a quicksort       ││ 输入> 帮我写一个快速排序          │
│                                    ││   → Help me write a quicksort    │
│ ● Sure, here's a quicksort        ││                                  │
│   implementation:                  ││ CC (EN):                         │
│                                    ││ Sure, here's a quicksort         │
│   def quicksort(arr):              ││ implementation:                  │
│       if len(arr) <= 1:            ││   def quicksort(arr):            │
│           return arr               ││       ...                        │
│       pivot = arr[0]               ││                                  │
│       ...                          ││ CC (中文):                       │
│                                    ││ 当然，这是一个快速排序的实现：    │
│                                    ││   def quicksort(arr):            │
│                                    ││       ...                        │
│                                    ││ ────────────────────────────     │
└────────────────────────────────────┘└──────────────────────────────────┘
```

</div>

## 为什么做这个？

很多中文开发者在用 Claude Code 时面临一个矛盾：

- 用中文提问更高效，但 **技术英文表达能力得不到提升**
- 用英文提问能学习，但 **效率太低、表达不准确**

**cc-bilingual** 解决这个矛盾：你用中文自然表达，它帮你翻译成地道的英文发给 CC。CC 的英文回复也会同时展示中文翻译。日积月累，你会在无意中掌握大量技术英文表达。

## 特性

- **零配置** — 不改任何配置文件，不需要 API Key，装完即用
- **无侵入** — 只读 CC 自己的对话日志，不注入 hooks，不修改 settings
- **双语对照** — CC 回复同时展示英文原文和中文翻译
- **代码感知** — 代码块永远不会被翻译，只翻译自然语言
- **智能透传** — `y`、`n`、`/help` 等短指令直接发给 CC，不翻译
- **零依赖** — 纯 Python 标准库，无需 `pip install` 任何东西
- **双向交互** — 两个窗口都可以操作，鼠标点击即可切换

## 快速开始

### 前置条件

- [Claude Code](https://github.com/anthropics/claude-code)（`claude` 命令可用）
- Python 3.8+
- tmux

```bash
# macOS
brew install tmux

# Ubuntu / Debian
sudo apt install tmux
```

### 安装

```bash
git clone https://github.com/user/cc-bilingual.git
cd cc-bilingual
chmod +x cc-bilingual.sh
```

可选：添加快捷命令

```bash
echo 'alias ccb="~/cc-bilingual/cc-bilingual.sh"' >> ~/.zshrc
source ~/.zshrc
```

### 启动

```bash
# 在当前目录启动
./cc-bilingual.sh

# 指定项目目录
./cc-bilingual.sh ~/my-project

# 如果设置了 alias
ccb ~/my-project
```

## 使用指南

### 基本操作

| 操作 | 说明 |
|------|------|
| 输入中文 | 自动翻译为英文，发送给 CC |
| 输入 `y` / `n` / 数字 | 直接透传给 CC，不翻译 |
| 输入 `/quit` | 退出 TUI |
| 输入 `/` 开头的命令 | 直接透传（如 `/help`、`/compact`）|
| 直接回车 | 发送空行给 CC（用于确认等） |

### 窗口切换

| 方式 | 操作 |
|------|------|
| 鼠标 | 直接点击左/右窗口 |
| 键盘 | `Ctrl-B` → 方向键（左/右）|

### TUI 输出格式

```
输入> 帮我优化这段代码的性能        ← 你的中文输入
  → Help me optimize the            ← 自动翻译的英文（发给了 CC）
    performance of this code

CC (EN):                             ← CC 的英文原文
Sure! Here are some optimizations
you can make: ...

CC (中文):                           ← 自动翻译的中文
当然！这是一些你可以做的优化：...
──────────────────────────────────────
```

## 工作原理

```
                    cc-bilingual
┌──────────────────────────────────────────────┐
│                                              │
│  你输入中文                                   │
│      │                                       │
│      ▼                                       │
│  Google Translate (zh → en)                  │
│      │                                       │
│      ▼                                       │
│  tmux send-keys ──────────────▶ Claude Code  │
│                                     │        │
│  ┌──────────────────────────────────┘        │
│  │                                           │
│  ▼                                           │
│  CC 写对话日志                                │
│  ~/.claude/projects/{project}/*.jsonl        │
│  │                                           │
│  ▼                                           │
│  TUI tail-watch 日志文件                      │
│  │                                           │
│  ├──▶ 显示英文原文                            │
│  │                                           │
│  └──▶ Google Translate (en → zh)             │
│       └──▶ 显示中文翻译                       │
│                                              │
└──────────────────────────────────────────────┘
```

**关键设计：**

- **不改任何配置** — 不注入 hooks，不修改 `settings.json`，不碰全局配置
- **只读日志文件** — CC 自己会把对话写入 `~/.claude/projects/` 下的 JSONL 文件，我们只是读它
- **翻译免费无限** — 使用 Google Translate 公共 API，无需注册，无需 Key

## 技术栈

| 组件 | 技术 | 说明 |
|------|------|------|
| TUI | Python 3 stdlib | 零外部依赖 |
| 双窗口 | tmux | 分屏 + 鼠标支持 |
| 翻译 | Google Translate API | 免费、无 Key、质量高 |
| IPC | 文件监听 | tail-watch CC 的 JSONL 日志 |

## 项目结构

```
cc-bilingual/
├── cc-bilingual.sh       # 启动入口
├── cc_translate.py       # 翻译核心（Google API + 代码块处理）
├── cc_tui.py             # 中文 TUI（输入处理 + 日志监听）
├── tests/
│   ├── test_translate.py # 翻译模块测试
│   └── test_tui.py       # TUI 逻辑测试
└── README.md
```

## FAQ

**Q: 为什么 CC 还是用中文回复？**

cc-bilingual 会在第一条消息自动附带 `(Please always respond in English.)`。如果 CC 仍然用中文回复，可能是你的全局 `~/.claude/settings.json` 里设置了 `"language": "中文"`。你可以在 CC 启动后手动发一条 "Please respond in English from now on" 来切换。

**Q: 翻译质量怎么样？**

使用 Google Translate，技术文本翻译质量不错。代码块不会被翻译，只翻译自然语言部分。

**Q: 有请求频率限制吗？**

正常使用不会触发限制。如果你在极短时间内发送大量请求，可能会被暂时限流。翻译失败时会显示原文，不影响使用。

**Q: 支持其他语言吗？**

目前硬编码为 中文 ↔ 英文。修改 `cc_tui.py` 中的语言代码即可支持其他语言（如 `ja` 日文、`ko` 韩文）。

**Q: 能不能不用 tmux？**

目前必须用 tmux 来实现双窗口。未来可能支持其他方案（如 iTerm2 split pane）。

## 贡献

欢迎 PR！尤其欢迎这些方向：

- 支持更多语言对
- 更好的 TUI 交互（如 `textual` 库）
- 支持不依赖 tmux 的方案
- 翻译引擎可切换（DeepL、本地模型等）

## License

[MIT](LICENSE)
