"""Host checks for P026 encoder startup. Not a physical S23 probe.

TC-P026-01..08 are specified elsewhere and are not executed by this module.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "gates"))

from p026_qualify_video_encoder_startup import (  # noqa: E402
    BASE_REVISION,
    EMITTED_STREAM,
    FIXTURE,
    METHOD,
    MUTANT,
    ORACLE,
    REQUESTED_MEDIAFORMAT,
    assess_startup,
    bit_depth,
    ten_bit_route_ok,
    validate_fixture,
)


RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
HANDOFF_KEYS = (
    "phase",
    "caseIds",
    "changedFiles",
    "commit",
    "testsRun",
    "failures",
    "unverified",
    "nextPhase",
)


def load_fixture() -> dict:
    path = ROOT / "docs" / "P026_QUALIFY_VIDEO_ENCODER_STARTUP.json"
    return json.loads(path.read_text(encoding="utf-8"))


def load_handoff() -> dict:
    path = ROOT / "docs" / "evidence" / "P026-handoff.json"
    return json.loads(path.read_text(encoding="utf-8"))


def matching_ten_bit(document: dict) -> dict:
    cloned = copy.deepcopy(document)
    cloned["emitted"]["bitDepth"] = 10
    cloned["emitted"]["spsBitDepth"] = 10
    for event in cloned["events"]:
        if event["kind"] == "codec_config":
            event["spsBitDepth"] = 10
    return cloned


class P026EncoderStartupTests(unittest.TestCase):
    def test_fixture_encodes_method_oracle_and_base_revision(self) -> None:
        raw = load_fixture()
        self.assertIsNone(validate_fixture(raw))
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P026")
        self.assertEqual(raw["contractId"], "s23-encoder-startup-fixture")
        self.assertEqual(raw["implementationBaseRevision"], BASE_REVISION)
        self.assertEqual(raw["method"], METHOD)
        self.assertEqual(raw["fixture"], FIXTURE)
        self.assertEqual(raw["oracle"], ORACLE)
        self.assertEqual(raw["mutant"], MUTANT)
        self.assertEqual(raw["request"]["profile"], "Main10")
        self.assertEqual(raw["request"]["bitDepth"], 10)
        self.assertTrue(raw["configure"]["succeeded"])
        self.assertEqual(raw["configure"]["mediaFormatBitDepth"], 10)
        self.assertEqual(raw["emitted"]["spsBitDepth"], 8)
        self.assertFalse(raw["emitted"]["relabelledAsAcceptableLog"])
        self.assertEqual(raw["request"]["logLabel"], "none")
        kinds = [event["kind"] for event in raw["events"]]
        self.assertEqual(
            kinds,
            ["format_change", "codec_config", "keyframe_request", "startup_timeout", "output_sample"],
        )
        self.assertTrue(all(event["handledSeparately"] is True for event in raw["events"]))

    def test_eight_bit_sps_fails_the_ten_bit_route(self) -> None:
        raw = load_fixture()
        self.assertEqual(bit_depth(raw, EMITTED_STREAM), 8)
        self.assertEqual(bit_depth(raw, REQUESTED_MEDIAFORMAT), 10)
        self.assertTrue(ten_bit_route_ok(raw, REQUESTED_MEDIAFORMAT))
        self.assertFalse(ten_bit_route_ok(raw, EMITTED_STREAM))
        result = assess_startup(raw)
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], "P026")
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "startup_ready"})
        self.assertIn("ten-bit-route-failed", result["rejectedClaims"])
        self.assertNotIn("silent-acceptable-log", result["rejectedClaims"])
        self.assertIn("main10-request", result["preservedResults"])
        self.assertIn("hevc-access-unit", result["preservedResults"])
        self.assertIn("c2.android.hevc.encoder", result["preservedResults"])
        self.assertIn("sps-bit-depth:8", result["preservedResults"])
        self.assertTrue(any("not silently relabelled as acceptable Log" in item for item in result["reasons"]))
        self.assertTrue(any("was not applied" in item for item in result["reasons"]))
        self.assertTrue(any("wrong signal" in item for item in result["reasons"]))
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))
        self.assertTrue(any("ten-bit fidelity" in item for item in result["openQuestions"]))

    def test_mutant_mediaformat_depth_does_not_become_startup_ready(self) -> None:
        raw = load_fixture()
        self.assertTrue(ten_bit_route_ok(raw, REQUESTED_MEDIAFORMAT))
        result = assess_startup(raw)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotEqual(result["decision"], "startup_ready")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        honest = ten_bit_route_ok(raw, EMITTED_STREAM)
        self.assertFalse(honest)

    def test_matching_emitted_ten_bit_is_startup_ready_not_qualified(self) -> None:
        ready = matching_ten_bit(load_fixture())
        self.assertTrue(ten_bit_route_ok(ready, EMITTED_STREAM))
        self.assertTrue(ten_bit_route_ok(ready, REQUESTED_MEDIAFORMAT))
        result = assess_startup(ready)
        self.assertEqual(result["decision"], "startup_ready")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("sps-bit-depth:10", result["preservedResults"])
        self.assertIn("main10-request", result["preservedResults"])
        self.assertTrue(any("not physical qualification" in item for item in result["reasons"]))

    def test_silent_log_relabel_is_rejected(self) -> None:
        raw = load_fixture()
        raw["emitted"]["relabelledAsAcceptableLog"] = True
        result = assess_startup(raw)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("silent-acceptable-log", result["rejectedClaims"])
        self.assertIn("ten-bit-route-failed", result["rejectedClaims"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "startup_ready"})
        self.assertIn("hevc-access-unit", result["preservedResults"])

    def test_config_failure_keeps_the_diagnostic_and_the_inventory(self) -> None:
        raw = load_fixture()
        raw["configure"]["succeeded"] = False
        raw["advertisedCodec"]["configFailureReason"] = "encoder did not accept Main10"
        result = assess_startup(raw)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("advertised-codec-config-failed", result["rejectedClaims"])
        self.assertTrue(any("encoder did not accept Main10" in item for item in result["reasons"]))
        self.assertIn("main10-request", result["preservedResults"])
        self.assertIn("c2.android.hevc.encoder", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "startup_ready"})

    def test_folded_format_change_is_rejected_even_when_depth_matches(self) -> None:
        ready = matching_ten_bit(load_fixture())
        for event in ready["events"]:
            if event["kind"] == "format_change":
                event["handledSeparately"] = False
        result = assess_startup(ready)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("format_change-not-separate", result["rejectedClaims"])
        self.assertNotIn("ten-bit-route-failed", result["rejectedClaims"])
        self.assertNotEqual(result["decision"], "startup_ready")
        self.assertIn("hevc-access-unit", result["preservedResults"])

    def test_startup_timeout_is_separate_from_the_signal(self) -> None:
        ready = matching_ten_bit(load_fixture())
        for event in ready["events"]:
            if event["kind"] == "startup_timeout":
                event["fired"] = True
                event["elapsedMs"] = 1500
        result = assess_startup(ready)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("startup-timeout", result["rejectedClaims"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "startup_ready"})
        self.assertIn("sps-bit-depth:10", result["preservedResults"])

    def test_invalid_fixtures_raise(self) -> None:
        valid = load_fixture()
        extra = copy.deepcopy(valid)
        extra["note"] = "device probe"
        missing = copy.deepcopy(valid)
        del missing["mutant"]
        wrong_phase = copy.deepcopy(valid)
        wrong_phase["phase"] = "P025"
        drifted = copy.deepcopy(valid)
        drifted["emitted"]["bitDepth"] = 10
        relabel = copy.deepcopy(valid)
        relabel["emitted"]["relabelledAsAcceptableLog"] = "yes"
        cases = (None, [], {}, extra, missing, wrong_phase, drifted, relabel)
        for sample in cases:
            with self.subTest(sample=type(sample).__name__):
                with self.assertRaises(ValueError):
                    validate_fixture(sample)

    def test_handoff_and_note_do_not_claim_qualification(self) -> None:
        handoff = load_handoff()
        self.assertEqual(tuple(handoff), HANDOFF_KEYS)
        self.assertEqual(handoff["phase"], "P026")
        self.assertEqual(handoff["caseIds"], [f"TC-P026-0{index}" for index in range(1, 9)])
        self.assertIsNone(handoff["commit"])
        self.assertEqual(handoff["failures"], [])
        self.assertEqual(handoff["nextPhase"], "P027")
        self.assertIn(
            "python3 -m unittest discover -s scripts/tests -p 'test_p026*.py' -v",
            handoff["testsRun"],
        )
        self.assertIn("physical S23 capture", handoff["unverified"])
        self.assertIn("ten-bit fidelity", handoff["unverified"])
        self.assertIn("cinema-camera equivalence", handoff["unverified"])
        for relative in handoff["changedFiles"]:
            self.assertTrue((ROOT / relative).is_file(), relative)
        note = (ROOT / "docs" / "P026_QUALIFY_VIDEO_ENCODER_STARTUP.md").read_text(encoding="utf-8")
        self.assertIn("python3 -m unittest discover -s scripts/tests -p 'test_p026*.py' -v", note)
        self.assertIn("not a physical S23", note)
        self.assertIn("ten-bit fidelity", note)
        self.assertIn("sensor-derived Log", note)


if __name__ == "__main__":
    unittest.main()
