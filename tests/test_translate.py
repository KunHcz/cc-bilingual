"""Tests for cc_translate module."""
import sys
import os
import unittest

# Ensure the project root is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


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


from unittest.mock import patch, MagicMock
import json as _json


class TestTranslate(unittest.TestCase):

    def _mock_google_response(self, translation_text):
        """Mock Google Translate API response: [[[translated, original, ...],...], ...]"""
        payload = [[[translation_text, "source text", None, None, 10]], None, "en"]
        mock_resp = MagicMock()
        mock_resp.read.return_value = _json.dumps(payload).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        return mock_resp

    @patch("cc_translate.urllib.request.urlopen")
    def test_basic_translation(self, mock_urlopen):
        from cc_translate import translate
        mock_urlopen.return_value = self._mock_google_response("你好世界")
        result = translate("Hello World", "en", "zh-CN")
        self.assertEqual(result, "你好世界")

    @patch("cc_translate.urllib.request.urlopen")
    def test_empty_text(self, mock_urlopen):
        from cc_translate import translate
        result = translate("", "en", "zh-CN")
        self.assertEqual(result, "")
        mock_urlopen.assert_not_called()

    @patch("cc_translate.urllib.request.urlopen")
    def test_api_failure_returns_original(self, mock_urlopen):
        from cc_translate import translate
        mock_urlopen.side_effect = Exception("Network error")
        result = translate("Hello", "en", "zh-CN")
        self.assertEqual(result, "Hello")

    @patch("cc_translate.urllib.request.urlopen")
    def test_long_text_no_chunk_under_500(self, mock_urlopen):
        from cc_translate import translate
        mock_urlopen.return_value = self._mock_google_response("翻译结果")
        long_text = "Short paragraph one.\n\nShort paragraph two."
        # Under 500 chars total, no chunking - single call
        result = translate(long_text, "en", "zh-CN")
        self.assertEqual(mock_urlopen.call_count, 1)

    @patch("cc_translate.urllib.request.urlopen")
    def test_long_text_splits_by_paragraph(self, mock_urlopen):
        from cc_translate import translate
        mock_urlopen.return_value = self._mock_google_response("翻译")
        para = "A" * 300
        long_text = f"{para}\n\n{para}"  # 600+ chars total
        result = translate(long_text, "en", "zh-CN")
        self.assertEqual(mock_urlopen.call_count, 2)

    @patch("cc_translate.urllib.request.urlopen")
    def test_multi_sentence_concatenation(self, mock_urlopen):
        """Google API returns multiple sentence segments; they should be joined."""
        from cc_translate import translate
        payload = [[["你好", "Hello", None, None, 10], ["世界", "World", None, None, 10]], None, "en"]
        mock_resp = MagicMock()
        mock_resp.read.return_value = _json.dumps(payload).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp
        result = translate("Hello World", "en", "zh-CN")
        self.assertEqual(result, "你好世界")


class TestTranslateMixed(unittest.TestCase):

    @patch("cc_translate.urllib.request.urlopen")
    def test_text_only(self, mock_urlopen):
        from cc_translate import translate_mixed
        payload = [[["你好", "Hello", None, None, 10]], None, "en"]
        mock_resp = MagicMock()
        mock_resp.read.return_value = _json.dumps(payload).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = translate_mixed("Hello", "en", "zh-CN")
        self.assertEqual(result, "你好")

    @patch("cc_translate._translate_single")
    def test_code_blocks_preserved(self, mock_translate):
        from cc_translate import translate_mixed
        mock_translate.return_value = "翻译文本"

        text = "Explanation:\n```python\nprint('hi')\n```\nDone."
        result = translate_mixed(text, "en", "zh-CN")
        self.assertIn("```python\nprint('hi')\n```", result)
        self.assertIn("翻译文本", result)

    @patch("cc_translate._translate_single")
    def test_only_code_no_translation(self, mock_translate):
        from cc_translate import translate_mixed
        code = "```python\nprint('hi')\n```"
        result = translate_mixed(code, "en", "zh-CN")
        self.assertEqual(result, code)
        mock_translate.assert_not_called()


if __name__ == "__main__":
    unittest.main()
