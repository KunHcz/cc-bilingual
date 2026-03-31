"""Tests for cc_tui module."""
import json
import os
import sys
import tempfile
import time
import threading
import unittest

# Ensure the project root is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestLogWatcher(unittest.TestCase):
    def test_reads_new_lines(self):
        from cc_tui import watch_logfile
        received = []
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            logpath = f.name
            f.write(json.dumps({"role": "assistant", "text": "old"}) + "\n")
            f.flush()
        try:
            t = threading.Thread(target=watch_logfile, args=(logpath, lambda d: received.append(d)), daemon=True)
            t.start()
            time.sleep(0.5)
            with open(logpath, 'a') as f:
                f.write(json.dumps({"role": "assistant", "text": "new"}) + "\n")
            time.sleep(1)
            texts = [d["text"] for d in received]
            self.assertIn("new", texts)
            self.assertNotIn("old", texts)  # started at EOF
        finally:
            os.unlink(logpath)


class TestDedup(unittest.TestCase):
    def test_recent_send_is_skipped(self):
        from cc_tui import should_skip_user_message, record_sent, _recent_sends
        _recent_sends.clear()
        record_sent("Hello World")
        self.assertTrue(should_skip_user_message("Hello World"))

    def test_old_send_not_skipped(self):
        from cc_tui import should_skip_user_message, _recent_sends
        _recent_sends.clear()
        _recent_sends.append((time.time() - 10, "Old message"))
        self.assertFalse(should_skip_user_message("Old message"))

    def test_different_text_not_skipped(self):
        from cc_tui import should_skip_user_message, record_sent, _recent_sends
        _recent_sends.clear()
        record_sent("Hello")
        self.assertFalse(should_skip_user_message("Goodbye"))


if __name__ == "__main__":
    unittest.main()
