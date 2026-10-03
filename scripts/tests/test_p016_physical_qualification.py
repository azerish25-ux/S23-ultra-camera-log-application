#!/usr/bin/env python3
"""P016 host-contract tests. These fixtures are not physical S23 evidence."""
from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import unittest

MODULE_PATH = Path(__file__).parents[1] / "p016_physical_qualification.py"
SPEC = importlib.util.spec_from_file_location("p016_physical_qualification", MODULE_PATH)
assert SPEC and SPEC.loader
p016 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(p016)

REVISION = "a" * 40
IDENTITY = {"algorithm": "SHA-256", "sha256": "b" * 64, "byteCount": 123456}


def fixture() -> dict:
    selected_mode = {
        "key": "1920x1080-30-SDR-avc-direct",
        "width": 1920,
        "height": 1080,
        "fps": 30,
        "dynamicRange": "SDR",
        "processing": "DIRECT",
        "encoder": "c2.exynos.avc.encoder",
        "mime": "video/avc",
        "bitrate": 12_000_000,
        "rateControl": "AE_FIXED",
        "requiresManualExposure": False,
    }
    verification = {
        "firstSyncFrameDecoded": True,
        "firstAudioPcmDecoded": True,
        "audioRequested": True,
        "audioTrackCount": 1,
        "sampleSpanUs": 60_100_000,
        "mediaIdentity": copy.deepcopy(IDENTITY),
        "cadenceStatus": "within_tolerance",
        "largeFrameIntervals": 0,
    }
    validation = {
        "schemaVersion": 3,
        "kind": "recording-validation",
        "status": "checked",
        "videoOnly": False,
        "audioMode": "MONO",
        "selectedMode": copy.deepcopy(selected_mode),
        "verification": verification,
    }
    attempt = {
        "schemaVersion": 1,
        "kind": "ordinary-recording-evidence",
        "sourceRevision": REVISION,
        "closed": True,
        "classification": {
            "recordingSucceeded": True,
            "fullDecodeVerified": False,
            "physicalCameraCertified": False,
        },
    }
    device = {
        "capturedAtUtc": "2026-10-03T12:00:00Z",
        "manufacturer": "samsung",
        "brand": "samsung",
        "model": "SM-S918W",
        "device": "dm3q",
        "product": "dm3qcsx",
        "fingerprint": "samsung/dm3qcsx/dm3q:16/test/release-keys",
        "sdkInt": 36,
        "androidRelease": "16",
        "securityPatch": "2026-09-01",
        "elapsedRealtimeMs": 123456,
        "internalAvailableBytes": 40_000_000_000,
        "externalAvailableBytes": 40_000_000_000,
        "thermalStatus": 0,
        "battery": {"percent": 80.0, "temperatureC": 27.0, "voltageMv": 4200, "status": 3,
                    "health": 2, "plugged": 0, "present": True},
    }
    return {
        "schemaVersion": 1,
        "kind": p016.KIND,
        "phase": "P016",
        "caseIds": [f"TC-P016-{number:02d}" for number in range(1, 9)],
        "runId": "20261003T120000Z-aaaaaaaaaaaa",
        "sourceRevision": REVISION,
        "recordingStartUtc": "2026-10-03T12:00:01Z",
        "recordingEndUtc": "2026-10-03T12:01:07Z",
        "deviceBefore": copy.deepcopy(device),
        "deviceAfter": {**copy.deepcopy(device), "capturedAtUtc": "2026-10-03T12:01:08Z",
                        "elapsedRealtimeMs": 189456, "internalAvailableBytes": 39_900_000_000,
                        "externalAvailableBytes": 39_900_000_000, "thermalStatus": 2,
                        "battery": {**device["battery"], "percent": 78.0, "temperatureC": 32.0}},
        "route": {"key": "0:logical", "logicalId": "0", "physicalId": None, "front": False},
        "selectedMode": selected_mode,
        "catalogErrors": [],
        "markerProtocol": {"id": p016.MARKER_PROTOCOL, "operatorConfirmedReady": True,
                           "expectedEventsSeconds": [10, 20, 30, 40, 50, 60],
                           "deviceStatus": "awaiting_host_detection"},
        "captureValidation": validation,
        "recordingAttempt": attempt,
        "files": {
            "media": {"name": "capture.mp4", "identity": copy.deepcopy(IDENTITY)},
            "recordingValidation": {"name": "recording-validation.json",
                                    "identity": {"algorithm": "SHA-256", "sha256": "c" * 64, "byteCount": 1000}},
            "recordingAttempt": {"name": "recording-attempt.json",
                                 "identity": {"algorithm": "SHA-256", "sha256": "d" * 64, "byteCount": 1000}},
        },
        "onDeviceAssessment": {
            "durationAtLeast60Seconds": True,
            "oneAudioTrackRequestedAndObserved": True,
            "firstVideoFrameDecoded": True,
            "firstAudioPcmDecoded": True,
            "fullDecodeVerified": False,
            "markerEventsVerified": False,
            "physicalConfigurationQualified": False,
            "enduranceCertified": False,
            "higherResolutionQualified": False,
            "status": "pending_off_device_full_decode_and_marker_analysis",
        },
        "nonClaims": [
            "This single run is not endurance or unlimited recording certification.",
            "It does not qualify higher-resolution modes.",
            "It does not qualify sensor-derived Log.",
            "It does not establish cinema-camera equivalence.",
        ],
    }


def media() -> dict:
    return {
        "fullDecodePassed": True,
        "audioPresent": True,
        "audioFullDecodePassed": True,
        "durationSeconds": 65.0,
        "packetSpanSeconds": 64.95,
        "stream": {"width": 1920, "height": 1080, "codec_name": "h264"},
        "mediaIdentity": copy.deepcopy(IDENTITY),
    }


def marker() -> dict:
    return {"protocol": p016.MARKER_PROTOCOL, "verified": True, "pairedEventCount": 5,
            "physicalLipSyncVerified": False}


def cadence(status: str = "pass") -> dict:
    return {"status": status, "requestedFps": 30, "measuredPacketFps": 29.998,
            "largeIntervals": 0 if status == "pass" else 1, "shortIntervals": 0}


class P016PhysicalQualificationTest(unittest.TestCase):
    def test_tc_p016_01_partial_property_failure_cannot_erase_valid_slice(self) -> None:
        document = fixture()
        document["catalogErrors"] = ["optional focal metadata query failed"]
        self.assertEqual(p016.validate_manifest(document, REVISION)["route"]["logicalId"], "0")

    def test_tc_p016_02_first_frame_only_cannot_qualify(self) -> None:
        candidate = media()
        candidate["fullDecodePassed"] = False
        with self.assertRaisesRegex(p016.QualificationError, "fully decoded"):
            p016.classify(p016.validate_manifest(fixture(), REVISION), candidate, marker(), cadence())

    def test_tc_p016_03_rear_conservative_combination_is_required(self) -> None:
        document = fixture()
        document["route"]["front"] = True
        with self.assertRaisesRegex(p016.QualificationError, "rear route"):
            p016.validate_manifest(document, REVISION)

    def test_tc_p016_04_stale_firmware_or_revision_is_rejected(self) -> None:
        document = fixture()
        document["recordingAttempt"]["sourceRevision"] = "e" * 40
        with self.assertRaisesRegex(p016.QualificationError, "revision is stale"):
            p016.validate_manifest(document, REVISION)
        with self.assertRaisesRegex(p016.QualificationError, "does not match"):
            p016.validate_manifest(fixture(), "f" * 40)

    def test_tc_p016_05_cadence_warning_is_not_hidden(self) -> None:
        result = p016.classify(p016.validate_manifest(fixture(), REVISION), media(), marker(), cadence("warning"))
        self.assertEqual(result["status"], "slice_retained_cadence_warning")
        self.assertFalse(result["cadenceQualifiedForThisSlice"])
        self.assertFalse(result["exactConfigurationQualified"])
        self.assertTrue(result["physicalSliceCompleted"])

    def test_tc_p016_06_output_geometry_mismatch_is_rejected(self) -> None:
        candidate = media()
        candidate["stream"]["width"] = 3840
        with self.assertRaisesRegex(p016.QualificationError, "geometry"):
            p016.classify(p016.validate_manifest(fixture(), REVISION), candidate, marker(), cadence())

    def test_tc_p016_07_audio_interface_is_independently_required(self) -> None:
        candidate = media()
        candidate["audioPresent"] = False
        candidate["audioFullDecodePassed"] = None
        with self.assertRaisesRegex(p016.QualificationError, "audio was not fully decoded"):
            p016.classify(p016.validate_manifest(fixture(), REVISION), candidate, marker(), cadence())

    def test_tc_p016_08_short_slice_never_becomes_endurance(self) -> None:
        result = p016.classify(p016.validate_manifest(fixture(), REVISION), media(), marker(), cadence())
        self.assertEqual(result["status"], "qualified_exact_60s_slice")
        self.assertTrue(result["exactConfigurationQualified"])
        self.assertFalse(result["enduranceCertified"])
        self.assertFalse(result["higherResolutionQualified"])
        self.assertFalse(result["sensorDerivedLogQualified"])
        self.assertFalse(result["physicalLipSyncVerified"])

    def test_marker_series_requires_two_repeating_pairs(self) -> None:
        video_times = [index / 30 for index in range(0, 1800)]
        brightness = [20.0] * len(video_times)
        for event in (10, 20, 30, 40, 50):
            first = int(event * 30)
            for index in range(first, first + 12):
                brightness[index] = 240.0
        audio_times = [index * 0.02 for index in range(0, 3000)]
        rms = [0.002] * len(audio_times)
        for event in (10.1, 20.1, 30.1, 40.1, 50.1):
            first = int(event / 0.02)
            for index in range(first, first + 20):
                rms[index] = 0.4
        result = p016.detect_marker_from_series(video_times, brightness, audio_times, rms)
        self.assertTrue(result["verified"])
        self.assertGreaterEqual(result["pairedEventCount"], 5)
        self.assertFalse(result["physicalLipSyncVerified"])

    def test_marker_absence_is_rejected(self) -> None:
        video_times = [index / 30 for index in range(0, 300)]
        audio_times = [index * 0.02 for index in range(0, 500)]
        with self.assertRaisesRegex(p016.QualificationError, "flash contrast"):
            p016.detect_marker_from_series(video_times, [20.0] * len(video_times),
                                           audio_times, [0.001] * len(audio_times))


if __name__ == "__main__":
    unittest.main()
