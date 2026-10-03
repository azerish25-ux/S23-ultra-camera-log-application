"""Host checks for the P023 interruption and permission policy.

Not a physical S23 probe. TC-P023-01..08 are specified elsewhere and are not
executed by the phase module.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "p023_handle_interruption_and_permission_changes",
    ROOT / "scripts" / "gates" / "p023_handle_interruption_and_permission_changes.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
assess_fixture = _MODULE.assess_fixture
evaluate = _MODULE.evaluate
mutant_payload = _MODULE.mutant_payload
validate_fixture = _MODULE.validate_fixture

BASE = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
FORBIDDEN = {"qualified", "allowed"}


def load_fixture() -> dict:
    path = ROOT / "docs" / "P023_HANDLE_INTERRUPTION_AND_PERMISSION_CHANGES.json"
    return json.loads(path.read_text(encoding="utf-8"))


def scenario(**overrides) -> dict:
    value = {
        "event": "permission_denial",
        "audioRequested": True,
        "videoSamples": 2,
        "audioSamples": 0,
        "visibleOutcome": "stop",
        "availableMediaRetained": True,
        "labelledSuccessfulAudio": False,
        "silentVideoOnlyContinuation": False,
        "backgroundDesignApproved": False,
        "takeId": "take-permission",
    }
    value.update(overrides)
    return value


class P023InterruptionPolicyTests(unittest.TestCase):
    def assert_contract(self, result) -> None:
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], "P023")
        self.assertNotIn(result["decision"], FORBIDDEN)
        self.assertIsInstance(result["reasons"], list)
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) for item in result[key]))

    def test_module_encodes_method_fixture_oracle_and_mutant(self) -> None:
        self.assertIn("permission denial", _MODULE.METHOD)
        self.assertIn("camera preemption", _MODULE.METHOD)
        self.assertIn("screen departure", _MODULE.METHOD)
        self.assertIn("app backgrounding", _MODULE.METHOD)
        self.assertIn("device policy restrictions", _MODULE.METHOD)
        self.assertIn("visible stop-and-finalize", _MODULE.METHOD)
        self.assertIn("Never silently remove a requested audio track.", _MODULE.METHOD)
        self.assertEqual(
            _MODULE.FIXTURE,
            "Microphone permission revoked during startup while video samples are already arriving.",
        )
        self.assertIn("cannot be labelled a successful audio recording", _MODULE.ORACLE)
        self.assertEqual(
            _MODULE.MUTANT,
            "Continue silently as video-only after requested microphone acquisition fails.",
        )
        self.assertEqual(_MODULE.BASE_REVISION, BASE)
        self.assertEqual(_MODULE.PHASE_ID, "P023")

    def test_fixture_matches_schema_and_oracle_stops_without_audio_success(self) -> None:
        raw = load_fixture()
        scenario_fields = validate_fixture(raw)
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P023")
        self.assertEqual(raw["implementationBaseRevision"], BASE)
        self.assertEqual(raw["policyId"], "s23-interruption-permission-fixture")
        self.assertEqual(raw["method"], _MODULE.METHOD)
        self.assertEqual(raw["fixture"], _MODULE.FIXTURE)
        self.assertEqual(raw["oracle"], _MODULE.ORACLE)
        self.assertEqual(raw["mutant"], _MODULE.MUTANT)
        self.assertIs(raw["backgroundDesignApproved"], False)
        self.assertEqual(raw["policy"], "visible-stop-and-finalize")
        self.assertEqual(scenario_fields["event"], "microphone_revoked_during_startup")
        self.assertGreaterEqual(scenario_fields["videoSamples"], 1)
        self.assertIs(scenario_fields["audioRequested"], True)
        self.assertIs(scenario_fields["silentVideoOnlyContinuation"], False)
        result = assess_fixture(raw)
        self.assert_contract(result)
        self.assertEqual(result["decision"], "stopped")
        self.assertIn("successful-audio-recording", result["rejectedClaims"])
        self.assertNotIn("silent-video-only", result["rejectedClaims"])
        self.assertIn(scenario_fields["takeId"], result["preservedResults"])
        self.assertIn(f"video-samples:{scenario_fields['videoSamples']}", result["preservedResults"])
        self.assertIn(f"audio-samples:{scenario_fields['audioSamples']}", result["preservedResults"])
        self.assertTrue(any("visible stop" in item for item in result["reasons"]))

    def test_visible_failure_is_not_qualification(self) -> None:
        raw = load_fixture()
        failed = copy.deepcopy(raw)
        failed["scenario"]["visibleOutcome"] = "fail"
        result = assess_fixture(failed)
        self.assert_contract(result)
        self.assertEqual(result["decision"], "failed_visible")
        self.assertNotIn(result["decision"], FORBIDDEN)
        self.assertIn("successful-audio-recording", result["rejectedClaims"])
        self.assertIn("take-startup-mic-revoked", result["preservedResults"])
        self.assertIn("video-samples:4", result["preservedResults"])

    def test_mutant_silent_video_only_is_rejected(self) -> None:
        raw = load_fixture()
        mutant = mutant_payload(raw["scenario"])
        result = evaluate(mutant)
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], FORBIDDEN | {"stopped", "failed_visible"})
        self.assertIn("silent-video-only", result["rejectedClaims"])
        self.assertIn("missing-visible-stop", result["rejectedClaims"])
        self.assertIn("take-startup-mic-revoked", result["preservedResults"])
        self.assertIn("video-samples:4", result["preservedResults"])
        self.assertIn("audio-samples:0", result["preservedResults"])
        joined = " ".join(result["reasons"])
        self.assertIn("silent video-only", joined)

    def test_mutant_would_fail_if_silent_continuation_were_accepted(self) -> None:
        """A gate that implemented the mutant would return stopped or allowed here."""
        payload = scenario(
            event="microphone_revoked_during_startup",
            videoSamples=4,
            takeId="take-startup-mic-revoked",
            silentVideoOnlyContinuation=True,
            visibleOutcome="continue",
        )
        result = evaluate(payload)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("silent-video-only", result["rejectedClaims"])
        self.assertNotEqual(result["decision"], "stopped")
        self.assertNotIn(result["decision"], FORBIDDEN)

    def test_permission_denial_stops_and_keeps_samples(self) -> None:
        result = evaluate(scenario())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "stopped")
        self.assertIn("take-permission", result["preservedResults"])
        self.assertIn("video-samples:2", result["preservedResults"])
        self.assertIn("successful-audio-recording", result["rejectedClaims"])

    def test_camera_preemption_of_video_only_stops_without_audio_claim(self) -> None:
        result = evaluate(
            scenario(
                event="camera_preemption",
                audioRequested=False,
                videoSamples=6,
                audioSamples=0,
                takeId="take-preempt",
            )
        )
        self.assertEqual(result["decision"], "stopped")
        self.assertNotIn(result["decision"], FORBIDDEN)
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("video-samples:6", result["preservedResults"])
        self.assertIn("take-preempt", result["preservedResults"])

    def test_screen_departure_and_device_policy_stop_visibly(self) -> None:
        for event, take in (
            ("screen_departure", "take-screen"),
            ("device_policy", "take-policy"),
        ):
            result = evaluate(scenario(event=event, audioRequested=False, takeId=take, videoSamples=1))
            self.assertEqual(result["decision"], "stopped", event)
            self.assertIn(take, result["preservedResults"])
            self.assertNotIn(result["decision"], FORBIDDEN)

    def test_app_backgrounding_without_approval_must_stop(self) -> None:
        stopped = evaluate(
            scenario(event="app_backgrounding", audioRequested=False, takeId="take-bg", videoSamples=3)
        )
        self.assertEqual(stopped["decision"], "stopped")
        self.assertNotIn("qualified-background-recording", stopped["rejectedClaims"])
        continued = evaluate(
            scenario(
                event="app_backgrounding",
                audioRequested=False,
                takeId="take-bg",
                videoSamples=3,
                visibleOutcome="continue",
            )
        )
        self.assertEqual(continued["decision"], "rejected")
        self.assertIn("missing-visible-stop", continued["rejectedClaims"])
        self.assertNotIn(continued["decision"], FORBIDDEN)
        self.assertIn("video-samples:3", continued["preservedResults"])

    def test_claimed_background_approval_is_not_qualification(self) -> None:
        result = evaluate(
            scenario(
                event="app_backgrounding",
                audioRequested=False,
                backgroundDesignApproved=True,
                takeId="take-bg-claim",
            )
        )
        self.assertEqual(result["decision"], "stopped")
        self.assertNotIn(result["decision"], FORBIDDEN)
        self.assertIn("qualified-background-recording", result["rejectedClaims"])
        self.assertTrue(any("not qualification" in item for item in result["reasons"]))
        continued = evaluate(
            scenario(
                event="app_backgrounding",
                audioRequested=True,
                backgroundDesignApproved=True,
                visibleOutcome="continue",
                silentVideoOnlyContinuation=True,
                takeId="take-bg-mutant",
            )
        )
        self.assertEqual(continued["decision"], "rejected")
        self.assertIn("silent-video-only", continued["rejectedClaims"])
        self.assertIn("qualified-background-recording", continued["rejectedClaims"])
        self.assertNotIn(continued["decision"], FORBIDDEN)

    def test_labelled_successful_audio_is_rejected_and_media_remains(self) -> None:
        result = evaluate(scenario(labelledSuccessfulAudio=True, audioSamples=8, videoSamples=8))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("successful-audio-recording", result["rejectedClaims"])
        self.assertIn("video-samples:8", result["preservedResults"])
        self.assertIn("audio-samples:8", result["preservedResults"])
        self.assertNotIn(result["decision"], FORBIDDEN)

    def test_dropped_media_is_rejected_without_wiping_the_inventory(self) -> None:
        result = evaluate(scenario(availableMediaRetained=False, videoSamples=5, takeId="take-drop"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("dropped-available-media", result["rejectedClaims"])
        self.assertEqual(
            result["preservedResults"],
            ["take-drop", "video-samples:5", "audio-samples:0"],
        )

    def test_handoff_lists_phase_scope_without_a_physical_claim(self) -> None:
        handoff = json.loads((ROOT / "docs" / "evidence" / "P023-handoff.json").read_text(encoding="utf-8"))
        self.assertEqual(handoff["phase"], "P023")
        self.assertEqual(
            handoff["caseIds"],
            [f"TC-P023-0{index}" for index in range(1, 9)],
        )
        self.assertIn("scripts/gates/p023_handle_interruption_and_permission_changes.py", handoff["changedFiles"])
        self.assertEqual(handoff["failures"], 0)
        self.assertEqual(handoff["nextPhase"], "P024")
        self.assertIn("physical S23 capture", handoff["unverified"])
        self.assertTrue(handoff["testsRun"])
        blob = json.dumps(handoff).lower()
        self.assertNotIn("qualified physical", blob)

    def test_invalid_payloads_and_fixtures_raise(self) -> None:
        valid = scenario()
        samples = (
            None,
            [],
            {},
            {key: value for key, value in valid.items() if key != "takeId"},
            {**valid, "extra": True},
            {**valid, "event": "background"},
            {**valid, "audioRequested": "true"},
            {**valid, "videoSamples": True},
            {**valid, "videoSamples": -1},
            {**valid, "audioSamples": 1.5},
            {**valid, "visibleOutcome": "qualified"},
            {**valid, "labelledSuccessfulAudio": 1},
            {**valid, "silentVideoOnlyContinuation": 0},
            {**valid, "backgroundDesignApproved": "false"},
            {**valid, "takeId": ""},
            {**valid, "takeId": "has space"},
            {**valid, "event": "microphone_revoked_during_startup", "audioRequested": False, "videoSamples": 2},
            {**valid, "event": "microphone_revoked_during_startup", "videoSamples": 0},
            {**valid, "silentVideoOnlyContinuation": True, "visibleOutcome": "stop"},
            {**valid, "silentVideoOnlyContinuation": True, "audioRequested": False, "visibleOutcome": "continue"},
        )
        for item in samples:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)
        raw = load_fixture()
        extra = copy.deepcopy(raw)
        extra["note"] = "device"
        wrong_phase = copy.deepcopy(raw)
        wrong_phase["phase"] = "P022"
        mutant_doc = copy.deepcopy(raw)
        mutant_doc["scenario"]["silentVideoOnlyContinuation"] = True
        mutant_doc["scenario"]["visibleOutcome"] = "continue"
        approved = copy.deepcopy(raw)
        approved["backgroundDesignApproved"] = True
        for item in (None, [], extra, wrong_phase, mutant_doc, approved):
            with self.subTest(fixture=type(item).__name__):
                with self.assertRaises(ValueError):
                    validate_fixture(item)


if __name__ == "__main__":
    unittest.main()
