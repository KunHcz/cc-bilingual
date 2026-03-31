"""Tests for cc_tui conversation watcher and dedup logic."""
import json
import os
import sys
import tempfile
import time
import threading
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestFindSessionFile(unittest.TestCase):
    def test_finds_new_file(self):
        from cc_tui import find_session_file
        with tempfile.TemporaryDirectory() as tmpdir:
            old = os.path.join(tmpdir, "old.jsonl")
            with open(old, "w") as f:
                f.write("{}\n")
            new = os.path.join(tmpdir, "new.jsonl")
            with open(new, "w") as f:
                f.write("{}\n")
            # old is "existing", new is not
            result = find_session_file(tmpdir, existing_files={old})
            self.assertEqual(result, new)

    def test_waits_for_new_file(self):
        from cc_tui import find_session_file
        with tempfile.TemporaryDirectory() as tmpdir:
            old = os.path.join(tmpdir, "old.jsonl")
            with open(old, "w") as f:
                f.write("{}\n")

            def create_later():
                time.sleep(0.6)
                with open(os.path.join(tmpdir, "new.jsonl"), "w") as f:
                    f.write("{}\n")

            t = threading.Thread(target=create_later, daemon=True)
            t.start()
            result = find_session_file(tmpdir, existing_files={old})
            self.assertTrue(result.endswith("new.jsonl"))


class TestWatchConversation(unittest.TestCase):
    def test_reads_new_entries(self):
        from cc_tui import watch_conversation
        received = []
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            logpath = f.name
            f.write(json.dumps({"type": "user", "old": True}) + "\n")
            f.flush()
        try:
            t = threading.Thread(
                target=watch_conversation,
                args=(logpath, lambda d: received.append(d)),
                daemon=True,
            )
            t.start()
            time.sleep(0.5)
            with open(logpath, "a") as f:
                f.write(json.dumps({"type": "assistant", "new": True}) + "\n")
            time.sleep(1)
            self.assertTrue(any(d.get("new") for d in received))
            self.assertFalse(any(d.get("old") for d in received))
        finally:
            os.unlink(logpath)


class TestDedup(unittest.TestCase):
    def test_recent_send_is_skipped(self):
        from cc_tui import should_skip_user, record_sent, _recent_sends
        _recent_sends.clear()
        record_sent("Hello World")
        self.assertTrue(should_skip_user("Hello World"))

    def test_old_send_not_skipped(self):
        from cc_tui import should_skip_user, _recent_sends
        _recent_sends.clear()
        _recent_sends.append((time.time() - 20, "Old"))
        self.assertFalse(should_skip_user("Old"))

    def test_different_text_not_skipped(self):
        from cc_tui import should_skip_user, record_sent, _recent_sends
        _recent_sends.clear()
        record_sent("Hello")
        self.assertFalse(should_skip_user("Goodbye"))


if __name__ == "__main__":
    unittest.main()
