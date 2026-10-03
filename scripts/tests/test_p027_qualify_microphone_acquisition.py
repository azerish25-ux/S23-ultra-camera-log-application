"""Host checks for the P027 microphone acquisition contract. Not a physical S23 probe.

TC-P027-01..08 are specified elsewhere and are not executed by this module.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "gates"))

from p027_qualify_microphone_acquisition import (  # noqa: E402
    BASE_REVISION,
    FIXTURE,
    METHOD,
    MUTANT,
    ORACLE,
    assess_acquisition,
    evaluate,
    is_requested_stereo_mutant,
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
    path = ROOT / "docs" / "P027_QUALIFY_MICROPHONE_ACQUISITION.json"
    return json.loads(path.read_text(encoding="utf-8"))


def load_handoff() -> dict:
    path = ROOT / "docs" / "evidence" / "P027-handoff.json"
    return json.loads(path.read_text(encoding="utf-8"))


class P027MicrophoneAcquisitionTests(unittest.TestCase):
    def test_fixture_encodes_method_oracle_and_base_revision(self) -> None:
        raw = load_fixture()
        self.assertIsNone(validate_fixture(raw))
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P027")
        self.assertEqual(raw["contractId"], "s23-microphone-acquisition-fixture")
        self.assertEqual(raw["implementationBaseRevision"], BASE_REVISION)
        self.assertEqual(raw["method"], METHOD)
        self.assertEqual(raw["fixture"], FIXTURE)
        self.assertEqual(raw["oracle"], ORACLE)
        self.assertEqual(raw["mutant"], MUTANT)
        self.assertEqual(raw["queueLimitFrames"], 8)
        self.assertEqual(raw["sampleRateHz"], 48000)
        self.assertEqual(raw["pcmFormat"], "pcm_s16le")
        self.assertEqual(
            [item["id"] for item in raw["observations"]],
            ["stereo-request-mono-source", "blocked-encoder-stall"],
        )

    def test_stereo_request_reports_the_mono_source_and_the_blocked_encoder(self) -> None:
        raw = load_fixture()
        stereo, stalled = raw["observations"]
        self.assertEqual(stereo["requestedChannels"], 2)
        self.assertEqual(stereo["sourceChannels"], 1)
        self.assertEqual(stereo["reportedChannels"], 1)
        self.assertFalse(is_requested_stereo_mutant(stereo))
        self.assertEqual(stereo["clippedSamples"], 5)
        self.assertEqual(stereo["silencedSamples"], 2)
        self.assertTrue(stereo["clippingPreserved"])
        self.assertTrue(stereo["silencingPreserved"])
        self.assertTrue(stereo["aacSeparated"])
        self.assertTrue(stalled["encoderStalled"])
        self.assertTrue(stalled["acquisitionContinuing"])
        self.assertEqual(stalled["encoderDelayMs"], 240)
        self.assertEqual(stalled["missingMicrophoneMs"], 0)
        self.assertTrue(stalled["timingSeparated"])
        self.assertEqual(stalled["queuedFrames"], raw["queueLimitFrames"])
        self.assertFalse(is_requested_stereo_mutant(stalled))
        result = assess_acquisition(raw)
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], "P027")
        self.assertEqual(result["decision"], "actual_channels")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("stereo-request-mono-source", result["preservedResults"])
        self.assertIn("blocked-encoder-stall", result["preservedResults"])
        self.assertIn("source-channels:1", result["preservedResults"])
        self.assertIn("clipped-samples:5", result["preservedResults"])
        self.assertIn("silenced-samples:2", result["preservedResults"])
        self.assertIn("encoder-delay-ms:240", result["preservedResults"])
        self.assertIn("missing-microphone-ms:0", result["preservedResults"])
        self.assertIn("pcm_s16le", result["preservedResults"])
        joined = " ".join(result["reasons"])
        self.assertIn("actual channels 1", joined)
        self.assertIn("queue limits hold", joined)
        self.assertIn("distinct from missing microphone data", joined)
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))

    def test_mutant_reporting_requested_stereo_is_rejected(self) -> None:
        raw = load_fixture()
        mutant = copy.deepcopy(raw)
        for item in mutant["observations"]:
            item["reportedChannels"] = item["requestedChannels"]
            self.assertTrue(is_requested_stereo_mutant(item))
        result = assess_acquisition(mutant)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "actual_channels"})
        self.assertIn("requested-stereo-as-actual", result["rejectedClaims"])
        self.assertIn("actual-channels-not-reported", result["rejectedClaims"])
        self.assertIn("clipped-samples:5", result["preservedResults"])
        self.assertIn("silenced-samples:2", result["preservedResults"])
        self.assertIn("encoder-delay-ms:240", result["preservedResults"])
        self.assertIn("source-channels:1", result["preservedResults"])
        self.assertTrue(any(item.startswith("mutant:") for item in result["reasons"]))
        honest = assess_acquisition(raw)
        self.assertEqual(honest["decision"], "actual_channels")
        self.assertNotEqual(result["decision"], honest["decision"])

    def test_queue_breach_and_conflated_stall_keep_the_inventory(self) -> None:
        raw = load_fixture()
        breached = copy.deepcopy(raw)
        breached["observations"][1]["queuedFrames"] = 9
        breached["observations"][1]["timingSeparated"] = False
        breached["observations"][1]["acquisitionContinuing"] = False
        result = assess_acquisition(breached)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "actual_channels"})
        self.assertIn("queue-limit-exceeded", result["rejectedClaims"])
        self.assertIn("timing-not-distinguished", result["rejectedClaims"])
        self.assertIn("stall-treated-as-missing-microphone", result["rejectedClaims"])
        self.assertIn("queued-frames:9/8", result["preservedResults"])
        self.assertIn("clipped-samples:5", result["preservedResults"])
        self.assertIn("encoder-delay-ms:240", result["preservedResults"])
        self.assertIn("missing-microphone-ms:0", result["preservedResults"])

    def test_invisible_route_drift_and_erased_clipping_are_rejected(self) -> None:
        raw = load_fixture()
        drifted = copy.deepcopy(raw)
        drifted["observations"][0]["routeChanged"] = True
        drifted["observations"][0]["routePolicy"] = "invisible-drift"
        drifted["observations"][0]["clippingPreserved"] = False
        drifted["observations"][0]["silencingPreserved"] = False
        drifted["observations"][0]["aacSeparated"] = False
        result = assess_acquisition(drifted)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        for claim in (
            "invisible-route-drift",
            "clipping-erased",
            "silencing-erased",
            "aac-callback-merged",
        ):
            self.assertIn(claim, result["rejectedClaims"])
        self.assertIn("clipped-samples:5", result["preservedResults"])
        self.assertIn("silenced-samples:2", result["preservedResults"])
        self.assertIn("blocked-encoder-stall", result["preservedResults"])

    def test_permission_denial_stops_instead_of_continuing(self) -> None:
        raw = load_fixture()
        denied = copy.deepcopy(raw["observations"][0])
        denied["id"] = "permission-revoked"
        denied["microphonePermission"] = "denied"
        denied["acquisitionContinuing"] = False
        denied["routePolicy"] = "stop"
        denied["routeChanged"] = True
        stopped = evaluate(denied)
        self.assertEqual(stopped["decision"], "stopped")
        self.assertNotIn(stopped["decision"], {"qualified", "allowed", "actual_channels"})
        self.assertEqual(stopped["rejectedClaims"], [])
        self.assertIn("permission:denied", stopped["preservedResults"])
        self.assertIn("clipped-samples:5", stopped["preservedResults"])
        continuing = copy.deepcopy(denied)
        continuing["acquisitionContinuing"] = True
        continuing["routePolicy"] = "continue"
        rejected = evaluate(continuing)
        self.assertEqual(rejected["decision"], "rejected")
        self.assertIn("acquisition-without-permission", rejected["rejectedClaims"])
        self.assertIn("permission-without-stop", rejected["rejectedClaims"])
        self.assertIn("source-channels:1", rejected["preservedResults"])

    def test_invalid_fixtures_raise(self) -> None:
        valid = load_fixture()
        extra = copy.deepcopy(valid)
        extra["note"] = "device probe"
        missing = copy.deepcopy(valid)
        del missing["mutant"]
        wrong_phase = copy.deepcopy(valid)
        wrong_phase["phase"] = "P026"
        wrong_revision = copy.deepcopy(valid)
        wrong_revision["implementationBaseRevision"] = "fffd5c9a63cb732e103052acae29ae0c251585cc"
        wrong_method = copy.deepcopy(valid)
        wrong_method["method"] = "report requested stereo"
        empty = copy.deepcopy(valid)
        empty["observations"] = []
        duplicate = copy.deepcopy(valid)
        duplicate["observations"][1]["id"] = duplicate["observations"][0]["id"]
        bad_limit = copy.deepcopy(valid)
        bad_limit["observations"][0]["queueLimitFrames"] = 4
        bool_channels = copy.deepcopy(valid)
        bool_channels["observations"][0]["sourceChannels"] = True
        cases = (
            None,
            [],
            {},
            extra,
            missing,
            wrong_phase,
            wrong_revision,
            wrong_method,
            empty,
            duplicate,
            bad_limit,
            bool_channels,
        )
        for sample in cases:
            with self.subTest(sample=type(sample).__name__):
                with self.assertRaises(ValueError):
                    validate_fixture(sample)
        with self.assertRaises(ValueError):
            evaluate({**valid["observations"][0], "routePolicy": "drift"})

    def test_handoff_lists_cases_and_does_not_invent_a_commit(self) -> None:
        handoff = load_handoff()
        self.assertEqual(tuple(handoff), HANDOFF_KEYS)
        self.assertEqual(handoff["phase"], "P027")
        self.assertEqual(handoff["caseIds"], [f"TC-P027-0{index}" for index in range(1, 9)])
        self.assertIsNone(handoff["commit"])
        self.assertEqual(handoff["failures"], [])
        self.assertEqual(handoff["nextPhase"], "P028")
        self.assertIn(
            "python3 -m unittest discover -s scripts/tests -p 'test_p027*.py' -v",
            handoff["testsRun"],
        )
        self.assertIn("physical S23 capture", handoff["unverified"])
        self.assertIn("cinema-camera equivalence", handoff["unverified"])
        for relative in handoff["changedFiles"]:
            self.assertTrue((ROOT / relative).is_file(), relative)


if __name__ == "__main__":
    unittest.main()
