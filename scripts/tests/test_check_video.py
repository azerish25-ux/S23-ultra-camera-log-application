import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from check_video import inspect, validate_metadata


def fixture():
    return {"streams": [{"codec_type": "video", "codec_name": "h264", "width": 1280, "height": 720}],
            "format": {"duration": "2.1"}, "packets": [{"pts_time": str(t)} for t in (0, 1, 2)]}


class VideoChecks(unittest.TestCase):
    def test_valid_no_b_frame_recording(self):
        result = validate_metadata(fixture(), 2, False)
        self.assertEqual(result["packets"], 3)
        self.assertEqual(result["measuredPacketFps"], 1)
        self.assertNotIn("fullDecodePassed", result)

    def test_invalid_minimum(self):
        for value in (-1, float("nan"), float("inf")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_metadata(fixture(), value, False)

    def test_invalid_duration(self):
        for value in ("nan", "inf", "-1", "0", "0.5", "N/A"):
            data = fixture()
            data["format"]["duration"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_metadata(data, 1, False)

    def test_requires_all_packet_timestamps(self):
        data = fixture()
        del data["packets"][1]["pts_time"]
        with self.assertRaises(ValueError):
            validate_metadata(data, 1, False)

    def test_rejects_invalid_or_reordered_timestamps(self):
        for times in ((0,), (0, 0, 2), (0, 2, 1), (0, float("nan"), 2), (0, 1, float("inf"))):
            data = fixture()
            data["packets"] = [{"pts_time": str(t)} for t in times]
            with self.subTest(times=times), self.assertRaises(ValueError):
                validate_metadata(data, 1, False)

    def test_container_duration_cannot_replace_packet_span(self):
        data = fixture()
        data["format"]["duration"] = "65"
        with self.assertRaises(ValueError):
            validate_metadata(data, 60, False)

    def test_exactly_one_video_stream(self):
        for streams in ([], [{"codec_type": "audio"}], fixture()["streams"] * 2):
            data = fixture()
            data["streams"] = streams
            with self.subTest(streams=streams), self.assertRaises(ValueError):
                validate_metadata(data, 1, False)

    def test_invalid_dimensions(self):
        data = fixture()
        data["streams"][0]["width"] = 0
        with self.assertRaises(ValueError):
            validate_metadata(data, 1, False)

    def test_requires_every_hlg_tag_and_bit_depth(self):
        data = fixture()
        required = {"codec_name": "hevc", "color_space": "bt2020nc", "color_transfer": "arib-std-b67",
                    "color_primaries": "bt2020", "color_range": "tv", "pix_fmt": "yuv420p10le"}
        data["streams"][0].update(required)
        validate_metadata(data, 1, True)
        for key in required:
            invalid = copy.deepcopy(data)
            invalid["streams"][0].pop(key)
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_metadata(invalid, 1, True)

    def test_decodes_full_clip_not_one_frame(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "clip.mp4"
            path.write_bytes(b"fixture")
            with patch("check_video.subprocess.run", side_effect=[
                subprocess.CompletedProcess([], 0, json.dumps(fixture()), ""),
                subprocess.CompletedProcess([], 0, "", ""),
            ]) as run:
                self.assertTrue(inspect(path, 1, False)["fullDecodePassed"])
                args = run.call_args_list[1].args[0]
                self.assertEqual(args[0], "ffmpeg")
                self.assertIn("-xerror", args)
                self.assertEqual(args[args.index("-fps_mode") + 1], "passthrough")
                self.assertEqual(args[args.index("-enc_time_base") + 1], "demux")
                self.assertNotIn("-frames:v", args)
                self.assertNotIn("-t", args)

    def test_decode_error_does_not_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "clip.mp4"
            path.write_bytes(b"fixture")
            with patch("check_video.subprocess.run", side_effect=[
                subprocess.CompletedProcess([], 0, json.dumps(fixture()), ""),
                subprocess.CalledProcessError(1, ["ffmpeg"]),
            ]), self.assertRaises(subprocess.SubprocessError):
                inspect(path, 1, False)

    def test_missing_or_empty_video(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "clip.mp4"
            with self.assertRaises(ValueError):
                inspect(path, 1, False)
            path.touch()
            with self.assertRaises(ValueError):
                inspect(path, 1, False)
