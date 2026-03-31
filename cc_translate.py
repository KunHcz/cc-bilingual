"""Translation utilities for cc-bilingual.

Uses Google Translate unofficial API (no API key required, zero external deps).
"""

import json
import os
import re
import urllib.parse
import urllib.request

GOOGLE_TRANSLATE_URL = "https://translate.googleapis.com/translate_a/single"


def split_code_blocks(text):
    """Split text into (type, content) segments.

    type='code' for ```...``` blocks, 'text' for everything else.
    Returns a list of (type, content) tuples with empty parts removed.
    """
    # Pattern captures fenced code blocks including the backticks and language tag
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


def is_short_command(text):
    """Return True if text should be passed through without translation.

    Covers: empty/whitespace, single chars, short ASCII words (<=3 chars),
    known command words, and slash commands.
    """
    stripped = text.strip()
    if not stripped:
        return True
    # Short pure-ASCII token (up to 3 characters)
    if len(stripped) <= 3 and stripped.isascii():
        return True
    # Well-known short English command words
    if stripped.lower() in ('yes', 'no', 'exit', 'quit', 'help', 'clear'):
        return True
    # Slash commands like /quit, /help, /compact
    if stripped.startswith('/'):
        return True
    return False


def _translate_single(text, source, target):
    """Translate a single chunk via Google Translate unofficial API.

    Returns the translated string, or the original text on failure.

    API endpoint:
        GET https://translate.googleapis.com/translate_a/single
            ?client=gtx&sl={source}&tl={target}&dt=t&q={encoded_text}

    Response structure:
        [
          [
            [translated_segment, original_segment, ...],
            ...
          ],
          null,
          source_language
        ]

    Full translation = join d[0][i][0] for all i.
    """
    chunk = text.strip()
    if not chunk:
        return text
    try:
        params = urllib.parse.urlencode({
            "client": "gtx",
            "sl": source,
            "tl": target,
            "dt": "t",
            "q": chunk,
        })
        url = f"{GOOGLE_TRANSLATE_URL}?{params}"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 cc-bilingual/1.0"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            # data[0] is a list of [translated, original, ...] segments
            translated = "".join(seg[0] for seg in data[0])
            return translated
    except Exception:
        return text


def translate(text, source="en", target="zh-CN"):
    """Translate text using Google Translate unofficial API.

    For texts longer than 500 characters, splits by double-newlines (paragraphs)
    and translates each paragraph separately, then rejoins.
    Returns original text on API failure.
    """
    text = text.strip()
    if not text:
        return text
    if len(text) > 500:
        paragraphs = text.split('\n\n')
        translated_parts = []
        for para in paragraphs:
            if para.strip():
                translated_parts.append(_translate_single(para, source, target))
            else:
                translated_parts.append('')
        return '\n\n'.join(translated_parts)
    return _translate_single(text, source, target)


def translate_mixed(text, source="en", target="zh-CN"):
    """Translate only the text parts of mixed text+code content.

    Code blocks (```...```) are preserved unchanged.
    Text segments are translated via translate().
    """
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
