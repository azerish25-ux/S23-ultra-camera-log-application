"""Host checks for the P071 capture-priority scheduler. Not a physical S23 probe.

TC-P071-01..08 are specified elsewhere and are not executed by this module.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "gates"))

from p071_prioritize_reliable_capture_over_preview_quality import (  # noqa: E402
    BASE_REVISION,
    FIXTURE,
    HOST_LIMIT,
    MAP_ID,
    METHOD,
    MUTANT,
    MUTANT_PATH,
    ORACLE,
    assess,
    scheduler_faults,
    validate_document,
)


RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
FIXTURE_PATH = ROOT / "docs" / "P071_PRIORITIZE_RELIABLE_CAPTURE_OVER_PREVIEW_QUALITY.json"


def load_document() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


class P071CapturePriorityTests(unittest.TestCase):
    def assert_result(self, result) -> None:
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], "P071")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) and item for item in result[key]))

    def test_constants_encode_method_fixture_oracle_and_mutant(self) -> None:
        self.assertEqual(MAP_ID, "s23-capture-priority-scheduler-fixture")
        self.assertEqual(BASE_REVISION, "d4deac8fc82832fd23396a01065c5f0bf9da6670")
        self.assertIn("reduce monitoring work", METHOD)
        self.assertIn("lower inference frequency", METHOD)
        self.assertIn("pause optional effects", METHOD)
        self.assertIn("stop capture only under its own safety policy", METHOD)
        self.assertIn("Record which preview quality was active", METHOD)
        self.assertIn("Never silently alter the selected source recording mode mid-take", METHOD)
        self.assertEqual(
            FIXTURE,
            "Increasing inference load while the camera and encoder approach their measured timing budget.",
        )
        self.assertEqual(
            ORACLE,
            "The preview degrades visibly and source cadence remains intact until a "
            "separately documented capture limit is reached.",
        )
        self.assertEqual(MUTANT, "Lower recording resolution without changing the active mode label.")

    def test_fixture_degrades_preview_and_keeps_source_cadence(self) -> None:
        raw = load_document()
        self.assertIsNone(validate_document(raw))
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P071")
        self.assertEqual(raw["mapId"], MAP_ID)
        self.assertEqual(raw["implementationBaseRevision"], BASE_REVISION)
        self.assertEqual(raw["method"], METHOD)
        self.assertEqual(raw["fixture"], FIXTURE)
        self.assertEqual(raw["oracle"], ORACLE)
        self.assertEqual(raw["mutant"], MUTANT)
        self.assertEqual(raw["budget"]["inferenceLoad"], "increasing")
        self.assertEqual(raw["budget"]["timingHeadroom"], "approaching-limit")
        self.assertIs(raw["budget"]["captureLimitDocumented"], True)
        self.assertIs(raw["budget"]["captureLimitReached"], False)
        self.assertEqual(raw["source"]["modeLabel"], "uhd-24")
        self.assertEqual(raw["source"]["recordingResolution"], "3840x2160")
        self.assertEqual(raw["source"]["selectedResolution"], "3840x2160")
        self.assertIs(raw["source"]["cadenceIntact"], True)
        self.assertIs(raw["preview"]["recorded"], True)
        self.assertEqual(raw["preview"]["activeQuality"], "reduced")
        self.assertEqual(scheduler_faults(raw), [])
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "preview_degraded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "rejected", "capture_stopped"})
        self.assertIn(ORACLE, result["reasons"])
        self.assertIn(METHOD, result["reasons"])
        self.assertIn(HOST_LIMIT, result["reasons"])
        self.assertIn("preview degraded visibly and source cadence remained intact", result["reasons"])
        self.assertNotIn(MUTANT, result["reasons"])
        preserved = result["preservedResults"]
        self.assertIn("mode:uhd-24", preserved)
        self.assertIn("selected-resolution:3840x2160", preserved)
        self.assertIn("recording-resolution:3840x2160", preserved)
        self.assertIn("cadence-intact:true", preserved)
        self.assertIn("mid-take:true", preserved)
        self.assertIn("capture-limit-documented:true", preserved)
        self.assertIn("capture-limit-reached:false", preserved)
        self.assertIn("inference-load:increasing", preserved)
        self.assertIn("timing-headroom:approaching-limit", preserved)
        self.assertIn("preview-quality:reduced", preserved)
        self.assertIn("preview-recorded:true", preserved)
        self.assertIn("preview-degraded:true", preserved)
        self.assertIn("step:reduce-monitoring:order=1:applied=true", preserved)
        self.assertIn("step:lower-inference:order=2:applied=true", preserved)
        self.assertIn("step:pause-effects:order=3:applied=true", preserved)
        self.assertIn("step:stop-capture:order=4:applied=false", preserved)

    def test_mutant_path_rejects_silent_resolution_drop(self) -> None:
        raw = load_document()
        honest = assess(raw)
        mutant = assess(raw, path=MUTANT_PATH)
        self.assert_result(mutant)
        self.assertEqual(honest["decision"], "preview_degraded")
        self.assertEqual(mutant["decision"], "rejected")
        self.assertEqual(mutant["rejectedClaims"], ["silent-resolution-drop"])
        self.assertNotIn(mutant["decision"], {"qualified", "allowed", "preview_degraded", "capture_stopped", "withheld"})
        self.assertIn(MUTANT, mutant["reasons"])
        self.assertIn("recording resolution changed without changing the active mode label", mutant["reasons"])
        self.assertIn("mutant silent resolution drop was rejected without erasing the selected mode", mutant["openQuestions"])
        self.assertIn("mode:uhd-24", mutant["preservedResults"])
        self.assertIn("selected-resolution:3840x2160", mutant["preservedResults"])
        self.assertIn("recording-resolution:3840x2160", mutant["preservedResults"])
        self.assertIn("preview-quality:reduced", mutant["preservedResults"])
        self.assertIn("cadence-intact:true", mutant["preservedResults"])
        self.assertEqual(
            [item for item in honest["preservedResults"] if item.startswith("mode:") or item.startswith("selected-")],
            [item for item in mutant["preservedResults"] if item.startswith("mode:") or item.startswith("selected-")],
        )

    def test_lowered_resolution_without_relabel_is_rejected(self) -> None:
        raw = load_document()
        raw["source"]["recordingResolution"] = "1920x1080"
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["silent-resolution-drop"])
        self.assertNotEqual(result["decision"], "preview_degraded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertNotIn(MUTANT, result["reasons"])
        self.assertIn("mode:uhd-24", result["preservedResults"])
        self.assertIn("selected-resolution:3840x2160", result["preservedResults"])
        self.assertIn("recording-resolution:1920x1080", result["preservedResults"])
        self.assertEqual(json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))["source"]["recordingResolution"], "3840x2160")

    def test_documented_limit_stops_capture_without_changing_the_mode(self) -> None:
        raw = load_document()
        raw["budget"]["captureLimitReached"] = True
        raw["source"]["cadenceIntact"] = False
        raw["steps"][3]["applied"] = True
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "capture_stopped")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "preview_degraded"})
        self.assertIn("capture stopped under its documented safety policy", result["reasons"])
        self.assertIn("source cadence remained intact until the capture limit", result["reasons"])
        self.assertIn("mode:uhd-24", result["preservedResults"])
        self.assertIn("recording-resolution:3840x2160", result["preservedResults"])
        self.assertIn("selected-resolution:3840x2160", result["preservedResults"])
        self.assertIn("cadence-intact:false", result["preservedResults"])
        self.assertIn("capture-limit-reached:true", result["preservedResults"])
        self.assertIn("step:stop-capture:order=4:applied=true", result["preservedResults"])
        mutant = assess(raw, path=MUTANT_PATH)
        self.assertEqual(mutant["decision"], "rejected")
        self.assertIn("silent-resolution-drop", mutant["rejectedClaims"])
        self.assertNotEqual(mutant["decision"], "capture_stopped")

    def test_cadence_break_before_the_limit_is_rejected(self) -> None:
        raw = load_document()
        raw["source"]["cadenceIntact"] = False
        result = assess(raw)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["cadence-broken-before-limit"])
        self.assertIn("mode:uhd-24", result["preservedResults"])
        self.assertIn("recording-resolution:3840x2160", result["preservedResults"])
        self.assertIn("cadence-intact:false", result["preservedResults"])
        self.assertIn("capture-limit-reached:false", result["preservedResults"])

    def test_early_stop_and_skipped_order_keep_the_inventory(self) -> None:
        early = load_document()
        early["steps"][3]["applied"] = True
        early_result = assess(early)
        self.assertEqual(early_result["decision"], "rejected")
        self.assertEqual(early_result["rejectedClaims"], ["capture-stopped-early"])
        self.assertIn("step:stop-capture:order=4:applied=true", early_result["preservedResults"])
        self.assertIn("selected-resolution:3840x2160", early_result["preservedResults"])

        skipped = load_document()
        skipped["steps"][0]["applied"] = False
        skipped_result = assess(skipped)
        self.assertEqual(skipped_result["decision"], "rejected")
        self.assertIn("degradation-order", skipped_result["rejectedClaims"])
        self.assertIn("step:reduce-monitoring:order=1:applied=false", skipped_result["preservedResults"])
        self.assertIn("mode:uhd-24", skipped_result["preservedResults"])
        self.assertIn("preview-quality:reduced", skipped_result["preservedResults"])

    def test_undocumented_limit_and_unrecorded_preview_are_rejected(self) -> None:
        raw = load_document()
        raw["budget"]["captureLimitReached"] = True
        raw["budget"]["captureLimitDocumented"] = False
        raw["source"]["cadenceIntact"] = False
        raw["steps"][3]["applied"] = True
        result = assess(raw)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["undocumented-capture-limit"])
        self.assertIn("capture-limit-documented:false", result["preservedResults"])
        self.assertIn("mode:uhd-24", result["preservedResults"])

        quiet = load_document()
        quiet["preview"]["recorded"] = False
        quiet_result = assess(quiet)
        self.assertEqual(quiet_result["decision"], "rejected")
        self.assertEqual(quiet_result["rejectedClaims"], ["preview-quality-unrecorded"])
        self.assertIn("preview-quality:reduced", quiet_result["preservedResults"])
        self.assertIn("preview-recorded:false", quiet_result["preservedResults"])

    def test_idle_budget_is_withheld_without_dropping_the_mode(self) -> None:
        raw = load_document()
        raw["budget"]["inferenceLoad"] = "idle"
        raw["budget"]["timingHeadroom"] = "available"
        raw["preview"]["activeQuality"] = "full"
        raw["preview"]["degradedVisibly"] = False
        for step in raw["steps"]:
            step["applied"] = False
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "preview_degraded"})
        self.assertIn("mode:uhd-24", result["preservedResults"])
        self.assertIn("selected-resolution:3840x2160", result["preservedResults"])
        self.assertIn("recording-resolution:3840x2160", result["preservedResults"])
        self.assertIn("preview-quality:full", result["preservedResults"])
        self.assertIn("inference-load:idle", result["preservedResults"])
        self.assertIn("resource budget was not under the fixture stress, so the oracle was not applied", result["openQuestions"])

    def test_full_preview_under_stress_is_not_a_visible_degrade(self) -> None:
        raw = load_document()
        raw["preview"]["activeQuality"] = "full"
        raw["preview"]["degradedVisibly"] = False
        result = assess(raw)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["preview-not-degraded"])
        self.assertIn("preview-quality:full", result["preservedResults"])
        self.assertIn("recording-resolution:3840x2160", result["preservedResults"])

    def test_invalid_documents_and_paths_raise(self) -> None:
        valid = load_document()
        extra = copy.deepcopy(valid)
        extra["note"] = "device probe"
        missing = copy.deepcopy(valid)
        del missing["budget"]
        bad_phase = copy.deepcopy(valid)
        bad_phase["phase"] = "P070"
        bad_revision = copy.deepcopy(valid)
        bad_revision["implementationBaseRevision"] = "abc"
        numeric_size = copy.deepcopy(valid)
        numeric_size["source"]["recordingResolution"] = 3840
        bad_size = copy.deepcopy(valid)
        bad_size["source"]["selectedResolution"] = "3840X2160"
        bad_mode = copy.deepcopy(valid)
        bad_mode["source"]["modeLabel"] = "UHD"
        bad_quality = copy.deepcopy(valid)
        bad_quality["preview"]["activeQuality"] = "RGBA8"
        bad_order = copy.deepcopy(valid)
        bad_order["steps"][0]["order"] = True
        short_steps = copy.deepcopy(valid)
        short_steps["steps"] = short_steps["steps"][:3]
        bad_load = copy.deepcopy(valid)
        bad_load["budget"]["inferenceLoad"] = "high"
        bool_limit = copy.deepcopy(valid)
        bool_limit["budget"]["captureLimitReached"] = 1
        cases = (
            None,
            [],
            {},
            extra,
            missing,
            bad_phase,
            bad_revision,
            numeric_size,
            bad_size,
            bad_mode,
            bad_quality,
            bad_order,
            short_steps,
            bad_load,
            bool_limit,
        )
        for sample in cases:
            with self.subTest(sample=type(sample).__name__):
                with self.assertRaises(ValueError):
                    validate_document(sample)
        with self.assertRaises(ValueError):
            assess(valid, path="mutant")
        with self.assertRaises(ValueError):
            scheduler_faults(valid, path="allowed")


if __name__ == "__main__":
    unittest.main()
