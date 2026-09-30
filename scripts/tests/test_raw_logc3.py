import copy
import io
import json
import math
from pathlib import Path
import shutil
import struct
import sys
import tempfile
import unittest
import zlib

import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from raw_fixture import fixture
from raw_to_logc3 import (XYZ_TO_AWG3, demosaic, develop, encode, levels, load_json,
                         logc3_encode, logc3_decode, scan, timing, validate_profile)


class RawDeveloperTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.path, self.profile = fixture(self.folder, 64, 32, 3)
        self.seq = scan(self.path)

    def tearDown(self):
        self.temp.cleanup()

    def test_raw_records_and_timestamps(self):
        self.assertEqual(3, len(self.seq.frames))
        self.assertEqual(4096, self.seq.frames[0].size)
        self.assertEqual(0, self.seq.recovered_tail_bytes)
        self.assertTrue(timing(self.seq)["sourceWithinTolerance"])

    def test_published_logc3_points(self):
        self.assertAlmostEqual(.092809, float(logc3_encode(0)), places=8)
        self.assertAlmostEqual(.3910068, float(logc3_encode(.18)), places=6)
        self.assertGreater(float(logc3_encode(4)), float(logc3_encode(1)))
        self.assertLess(float(logc3_encode(-.01)), float(logc3_encode(0)))

    def test_curve_inverse_and_precision(self):
        values = np.linspace(-.01, 50, 10001)
        encoded = logc3_encode(values)
        np.testing.assert_allclose(values, logc3_decode(encoded), atol=2e-6, rtol=2e-6)
        self.assertTrue(np.all(np.diff(encoded) > 0))
        for value in [math.nan, math.inf]:
            with self.assertRaises(ValueError): logc3_encode(value)
            with self.assertRaises(ValueError): logc3_decode(value)
        codes = np.rint(logc3_encode(np.linspace(0, 4, 4096)) * 1023)
        self.assertGreater(len(np.unique(codes)), 256)
        eight_bit = np.rint(logc3_encode(np.linspace(0, 4, 4096)) * 255) * 1023 / 255
        self.assertLessEqual(len(np.unique(eight_bit)), 256)

    def test_awg3_not_bt2020_or_identity(self):
        matrix = np.array(self.profile["cameraToXyzD65"])
        np.testing.assert_allclose(XYZ_TO_AWG3 @ matrix, np.eye(3), atol=2e-6)
        self.assertGreater(abs(XYZ_TO_AWG3[0, 0] - 1), .5)

    def test_all_four_mosaics(self):
        from raw_to_logc3 import BAYER
        for cfa, pattern in enumerate(BAYER):
            values = {"R": .1, "G": .2, "B": .4}
            mosaic = np.zeros((8, 10), dtype=np.float32)
            for i, colour in enumerate(pattern):
                mosaic[i // 2::2, i % 2::2] = values[colour]
            actual = demosaic(mosaic, cfa)
            np.testing.assert_allclose(actual, np.broadcast_to([.1, .2, .4], actual.shape), atol=1e-7)

    def test_source_develops_without_8bit(self):
        profile = validate_profile(self.profile, self.seq)
        with self.path.open("rb") as source:
            image, clipping = develop(source, self.seq, self.seq.frames[0], profile)
        self.assertEqual((32, 64, 3), image.shape)
        self.assertEqual(0, clipping["outputAboveOne"])
        self.assertGreater(float(image.max()), .6)

    def test_corruption_is_not_recovery(self):
        data = bytearray(self.path.read_bytes())
        data[self.seq.frames[1].offset + 7] ^= 1
        self.path.write_bytes(data)
        for recover in (False, True):
            with self.assertRaisesRegex(ValueError, "checksum"): scan(self.path, recover)

    def test_truncated_tail_is_explicit(self):
        self.path.write_bytes(self.path.read_bytes()[:-9])
        with self.assertRaisesRegex(ValueError, "recover-tail"): scan(self.path)
        recovered = scan(self.path, True)
        self.assertEqual(2, len(recovered.frames))
        self.assertGreater(recovered.recovered_tail_bytes, 0)

    def test_invalid_magic_and_lengths(self):
        original = self.path.read_bytes()
        for data in (b"NOTRAW01" + original[8:], original[:8] + struct.pack("<I", 2**31) + original[12:]):
            self.path.write_bytes(data)
            with self.assertRaises(ValueError): scan(self.path)

    def test_profile_identity_is_exact(self):
        for key, value in [("fingerprint", "another firmware"), ("width", 66), ("physicalCamera", "other")]:
            profile = copy.deepcopy(self.profile); profile["source"][key] = value
            with self.assertRaisesRegex(ValueError, "bound"): validate_profile(profile, self.seq)

    def test_unmeasured_profile_is_not_silently_calibrated(self):
        profile = copy.deepcopy(self.profile); profile["calibration"]["status"] = "provisional"
        with self.assertRaisesRegex(ValueError, "Measured profile"): validate_profile(profile, self.seq)
        self.assertEqual("provisional", validate_profile(profile, self.seq, True)["status"])
        real_header = {**self.seq.header, "device": {**self.seq.header["device"], "model": "SM-S918"}}
        from dataclasses import replace
        with self.assertRaisesRegex(ValueError, "synthetic profile"):
            validate_profile(self.profile, replace(self.seq, header=real_header))

    def test_invalid_profile_values_and_exposure(self):
        for key, value in [("sceneScale", math.nan), ("sceneScale", 0), ("cameraToXyzD65", [[0] * 3] * 3),
                           ("bayerWhiteBalance", [1, 1, -1, 1]), ("crop", [1, 0, 60, 32]),
                           ("crop", [0, 0, 100, 32]), ("iso", 200)]:
            profile = copy.deepcopy(self.profile); profile[key] = value
            with self.assertRaises(ValueError): validate_profile(profile, self.seq)

    def test_missing_normalization_rejected(self):
        for meta in ({"blackLevels": [0] * 4, "whiteLevel": 0}, {"blackLevels": [20] * 4, "whiteLevel": 10},
                     {"blackLevels": [False] * 4, "whiteLevel": 1023}, {"blackLevels": [0] * 3, "whiteLevel": 1023}):
            with self.assertRaises(ValueError): levels(meta)
        with self.assertRaises(ValueError): load_json('{"bad":NaN}')

    def test_bad_cadence_needs_explicit_retime(self):
        from dataclasses import replace
        frames = list(self.seq.frames)
        frames[1] = replace(frames[1], metadata={**frames[1].metadata, "sensorTimestampNs": 1_070_000_000})
        sequence = replace(self.seq, frames=tuple(frames))
        with self.assertRaisesRegex(ValueError, "retiming"): timing(sequence)
        self.assertFalse(timing(sequence, True)["sourceWithinTolerance"])
        self.assertTrue(timing(sequence, True)["retimingExplicitlyAllowed"])

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg/FFprobe unavailable")
    def test_lossless_master_round_trip_and_no_overwrite(self):
        output = self.folder / "master.mkv"
        report = encode(self.seq, self.profile, output)
        self.assertEqual(3, report["decodedFrames"])
        self.assertTrue(report["losslessRgbVerified"])
        self.assertFalse(report["physicalCameraCertified"])
        self.assertFalse(report["arriSensorDynamicRangeClaimed"])
        self.assertEqual("synthetic", report["calibrationStatus"])
        self.assertTrue(output.with_suffix(".mkv.logc3.json").is_file())
        original = output.read_bytes()
        with self.assertRaisesRegex(ValueError, "overwritten"): encode(self.seq, self.profile, output)
        self.assertEqual(original, output.read_bytes())

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg/FFprobe unavailable")
    def test_real_hevc10_file_and_colour_contract(self):
        report = encode(self.seq, self.profile, self.folder / "tenbit.mp4", "hevc10")
        self.assertEqual("yuv420p10le", report["decodedPixelFormat"])
        self.assertEqual(10, report["storageBits"])
        self.assertEqual(3, report["decodedFrames"])
        self.assertTrue(report["fullDecodeVerified"])
        self.assertFalse(report["losslessRgbVerified"])

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg/FFprobe unavailable")
    def test_output_clipping_requires_permission(self):
        profile = copy.deepcopy(self.profile); profile["sceneScale"] = 1000
        output = self.folder / "clipped.mkv"
        with self.assertRaisesRegex(ValueError, "storage"): encode(self.seq, profile, output)
        self.assertFalse(output.exists())
        report = encode(self.seq, profile, output, allow_clipping=True)
        self.assertGreater(report["clipping"]["outputAboveOne"], 0)
