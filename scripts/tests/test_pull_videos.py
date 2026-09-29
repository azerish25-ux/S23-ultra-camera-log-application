from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pull_videos import pull_videos


class VideoTransferChecks(unittest.TestCase):
    def test_retries_only_transfer_and_discards_partial_attempt(self):
        with tempfile.TemporaryDirectory() as root:
            destination = Path(root) / "videos"
            attempts = []

            def run(args, **kwargs):
                self.assertLessEqual(kwargs["timeout"], 60)
                if args[1] == "pull":
                    staged = Path(args[-1])
                    self.assertFalse(staged.exists())
                    staged.mkdir()
                    attempts.append(staged)
                    if len(attempts) == 1:
                        (staged / "partial.mp4").write_bytes(b"partial")
                        raise subprocess.CalledProcessError(1, args, stderr="device offline")
                    (staged / "complete.mp4").write_bytes(b"complete")
                return subprocess.CompletedProcess(args, 0, "", "")

            with patch("pull_videos.subprocess.run", side_effect=run) as calls:
                pull_videos(destination)
                self.assertEqual(2, len(attempts))
                self.assertEqual(["complete.mp4"], [p.name for p in destination.iterdir()])
                self.assertFalse(attempts[0].exists())
                self.assertTrue(any(c.args[0] == ["adb", "reconnect", "offline"] for c in calls.call_args_list))
                self.assertTrue(all(c.args[0][0] == "adb" for c in calls.call_args_list))

    def test_permanent_failure_remains_failure_and_is_bounded(self):
        with tempfile.TemporaryDirectory() as root:
            destination = Path(root) / "videos"
            with patch("pull_videos.subprocess.run", side_effect=subprocess.CalledProcessError(1, ["adb"])) as run:
                with self.assertRaises(RuntimeError):
                    pull_videos(destination)
                self.assertEqual(5, run.call_count)  # three attempts, two reconnects
            self.assertFalse(destination.exists())
            self.assertEqual([], list(Path(root).iterdir()))

    def test_success_exit_without_files_does_not_pass(self):
        with tempfile.TemporaryDirectory() as root:
            destination = Path(root) / "videos"
            with patch("pull_videos.subprocess.run", return_value=subprocess.CompletedProcess([], 0, "", "")):
                with self.assertRaises(RuntimeError):
                    pull_videos(destination, attempts=1)
            self.assertFalse(destination.exists())

    def test_existing_evidence_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as root:
            destination = Path(root) / "videos"
            destination.mkdir()
            clip = destination / "keep.mp4"
            clip.write_bytes(b"keep")
            with patch("pull_videos.subprocess.run") as run:
                with self.assertRaises(ValueError):
                    pull_videos(destination)
                run.assert_not_called()
            self.assertEqual(b"keep", clip.read_bytes())
