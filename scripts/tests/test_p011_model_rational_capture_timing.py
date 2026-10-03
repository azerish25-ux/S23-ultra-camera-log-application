"""Host checks for the P011 rational timing policy. Not a physical S23 probe.

TC-P011-01..08 are specified elsewhere and are not executed by this module.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "gates"))

from p011_model_rational_capture_timing import (
    FIXTURE,
    METHOD,
    MUTANT,
    ORACLE,
    assess_policy,
    classify_mechanism,
    effective_interval_seconds,
    exposure_fits,
    retain_ae_upper,
    validate_policy,
)


BASE = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
FORBIDDEN = {"qualified", "allowed", "native_fixed_24"}


def load_policy() -> dict:
    path = ROOT / "docs" / "P011_MODEL_RATIONAL_CAPTURE_TIMING.json"
    return json.loads(path.read_text(encoding="utf-8"))


def rate(numerator: int, denominator: int = 1) -> dict:
    return {"numerator": numerator, "denominator": denominator}


class P011RationalTimingTests(unittest.TestCase):
    def assert_contract(self, result: dict) -> None:
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], "P011")
        self.assertNotIn(result["decision"], FORBIDDEN)
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) and item for item in result[key]))

    def test_module_encodes_method_fixture_oracle_and_mutant(self) -> None:
        self.assertIn("numerator and denominator", METHOD)
        self.assertIn("fixed AE ranges", METHOD)
        self.assertIn("variable AE ranges", METHOD)
        self.assertIn("manual frame duration", METHOD)
        self.assertIn("effective interval", METHOD)
        self.assertIn("capture-result timing", METHOD)
        self.assertIn("fifteen to thirty", FIXTURE)
        self.assertIn("twenty-four", FIXTURE)
        self.assertIn("has not been confirmed", FIXTURE)
        self.assertIn("native fixed twenty-four", ORACLE)
        self.assertIn("container timestamps", ORACLE)
        self.assertIn("AE upper bound", MUTANT)
        self.assertIn("cinematic frame rate", MUTANT)

    def test_fixture_withholds_native_fixed_24(self) -> None:
        raw = load_policy()
        self.assertIsNone(validate_policy(raw))
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P011")
        self.assertEqual(raw["policyId"], "s23-rational-timing-fixture")
        self.assertEqual(raw["implementationBaseRevision"], BASE)
        self.assertEqual(classify_mechanism(raw), "variable_ae")
        self.assertEqual(effective_interval_seconds(raw), rate(1, 30))
        self.assertIs(exposure_fits(raw), True)
        result = assess_policy(raw)
        self.assert_contract(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(
            result["preservedResults"],
            [
                "ae:15/1-30/1",
                "requested:24/1",
                "mechanism:variable_ae",
                "exposureNs:20000000",
                "manual:unconfirmed",
            ],
        )
        self.assertEqual(result["rejectedClaims"], ["container-timestamps-as-native-cadence"])
        self.assertIn("capture-result timing has not been measured", result["openQuestions"])
        self.assertIn("manual timing has not been confirmed", result["openQuestions"])
        self.assertIn(
            "variable AE range includes the requested rate without fixed-rate evidence",
            result["openQuestions"],
        )
        self.assertTrue(any("do not certify native fixed 24" in item for item in result["reasons"]))
        self.assertTrue(any("not rounded" in item for item in result["reasons"]))
        self.assertNotIn("native_fixed_24", result["decision"])

    def test_mutant_round_upper_to_24_is_rejected(self) -> None:
        raw = load_policy()
        result = assess_policy(raw, mutant="round-ae-upper-to-cinematic")
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["rounded-ae-upper-bound"])
        self.assertIn("ae:15/1-30/1", result["preservedResults"])
        self.assertNotIn("ae:15/1-24/1", result["preservedResults"])
        self.assertTrue(any("30/1" in item and "24/1" in item for item in result["reasons"]))
        self.assertNotIn(result["decision"], FORBIDDEN)

    def test_upper_bound_is_not_rounded_to_nearest_cinematic_rate(self) -> None:
        self.assertEqual(retain_ae_upper(rate(30), rate(24)), rate(30))
        self.assertEqual(retain_ae_upper(rate(22), rate(24)), rate(22))
        self.assertEqual(retain_ae_upper(rate(29), rate(24)), rate(29))
        self.assertEqual(retain_ae_upper(rate(30000, 1001), rate(24)), rate(30000, 1001))
        self.assertNotEqual(retain_ae_upper(rate(30), rate(24)), rate(24))
        self.assertNotEqual(retain_ae_upper(rate(22), rate(24)), rate(24))

    def test_exposure_uses_ae_ceiling_not_requested_24(self) -> None:
        raw = load_policy()
        raw["exposureNs"] = 40000000
        self.assertIs(exposure_fits(raw), False)
        result = assess_policy(raw)
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("exposure-exceeds-interval", result["rejectedClaims"])
        self.assertIn("ae:15/1-30/1", result["preservedResults"])
        self.assertIn("requested:24/1", result["preservedResults"])
        self.assertTrue(any("40000000ns" in item and "1/30s" in item for item in result["reasons"]))

    def test_same_exposure_fits_manual_24_and_is_not_ready_without_a_result(self) -> None:
        raw = load_policy()
        raw["mechanism"] = "manual"
        raw["manualTiming"] = {"confirmed": False, "frameRate": rate(24)}
        raw["exposureNs"] = 40000000
        self.assertEqual(classify_mechanism(raw), "manual")
        self.assertEqual(effective_interval_seconds(raw), rate(1, 24))
        self.assertIs(exposure_fits(raw), True)
        result = assess_policy(raw)
        self.assert_contract(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertNotIn("exposure-exceeds-interval", result["rejectedClaims"])
        self.assertIn("manual:24/1", result["preservedResults"])
        self.assertIn("manual timing awaiting capture-result confirmation", result["openQuestions"])
        self.assertIn("container-timestamps-as-native-cadence", result["rejectedClaims"])

    def test_manual_readiness_requires_a_matching_capture_result(self) -> None:
        raw = load_policy()
        raw["mechanism"] = "manual"
        raw["manualTiming"] = {"confirmed": False, "frameRate": rate(24)}
        raw["captureResult"] = {"frameRate": rate(24), "exposureNs": 20000000}
        result = assess_policy(raw)
        self.assert_contract(result)
        self.assertEqual(result["decision"], "manual_ready")
        self.assertIn("measured:24/1", result["preservedResults"])
        self.assertIn("container-timestamps-as-native-cadence", result["rejectedClaims"])
        self.assertNotIn("manual timing has not been confirmed", result["openQuestions"])
        self.assertTrue(any("matches the manual frame duration" in item for item in result["reasons"]))

    def test_manual_flag_alone_does_not_confirm_readiness(self) -> None:
        raw = load_policy()
        raw["mechanism"] = "manual"
        raw["manualTiming"] = {"confirmed": True, "frameRate": rate(24)}
        raw["containerTimestamps"] = {"assigned": False, "rate": None}
        result = assess_policy(raw)
        self.assertEqual(result["decision"], "withheld")
        self.assertNotIn(result["decision"], FORBIDDEN)
        self.assertIn("manual timing awaiting capture-result confirmation", result["openQuestions"])
        self.assertEqual(result["rejectedClaims"], [])

    def test_disagreeing_capture_result_is_not_assumed_applied(self) -> None:
        raw = load_policy()
        raw["mechanism"] = "manual"
        raw["manualTiming"] = {"confirmed": True, "frameRate": rate(24)}
        raw["captureResult"] = {"frameRate": rate(30), "exposureNs": 20000000}
        result = assess_policy(raw)
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("requested-not-applied", result["rejectedClaims"])
        self.assertIn("manual:24/1", result["preservedResults"])
        self.assertIn("measured:30/1", result["preservedResults"])

    def test_fixed_ae_without_a_capture_result_stays_withheld(self) -> None:
        raw = load_policy()
        raw["mechanism"] = "fixed_ae"
        raw["aeRange"] = {"minFps": rate(24), "maxFps": rate(24)}
        result = assess_policy(raw)
        self.assert_contract(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["preservedResults"][0], "ae:24/1-24/1")
        self.assertIn("container-timestamps-as-native-cadence", result["rejectedClaims"])
        self.assertNotEqual(result["decision"], "fixed_ae_observed")

    def test_fixed_ae_observation_comes_from_the_capture_result(self) -> None:
        raw = load_policy()
        raw["mechanism"] = "fixed_ae"
        raw["aeRange"] = {"minFps": rate(24), "maxFps": rate(24)}
        raw["captureResult"] = {"frameRate": rate(24), "exposureNs": 20000000}
        raw["containerTimestamps"] = {"assigned": False, "rate": None}
        result = assess_policy(raw)
        self.assertEqual(result["decision"], "fixed_ae_observed")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("measured:24/1", result["preservedResults"])
        self.assertNotIn(result["decision"], FORBIDDEN)

    def test_variable_range_stays_withheld_when_one_result_is_24(self) -> None:
        raw = load_policy()
        raw["captureResult"] = {"frameRate": rate(24), "exposureNs": 20000000}
        raw["containerTimestamps"] = {"assigned": False, "rate": None}
        result = assess_policy(raw)
        self.assertEqual(result["decision"], "withheld")
        self.assertIn("measured:24/1", result["preservedResults"])
        self.assertIn("ae:15/1-30/1", result["preservedResults"])
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(
            any("does not convert variable sensor timing" in item for item in result["reasons"])
        )

    def test_fractional_request_inside_the_range_is_not_rounded(self) -> None:
        raw = load_policy()
        raw["requestedOutput"] = rate(24000, 1001)
        raw["containerTimestamps"] = {"assigned": True, "rate": rate(24000, 1001)}
        result = assess_policy(raw)
        self.assertEqual(result["decision"], "withheld")
        self.assertIn("requested:24000/1001", result["preservedResults"])
        self.assertIn("ae:15/1-30/1", result["preservedResults"])
        self.assertNotIn(result["decision"], FORBIDDEN)
        self.assertEqual(retain_ae_upper(raw["aeRange"]["maxFps"], raw["requestedOutput"]), rate(30))

    def test_invalid_policies_and_mutants_raise(self) -> None:
        valid = load_policy()
        unreduced = copy.deepcopy(valid)
        unreduced["requestedOutput"] = {"numerator": 48, "denominator": 2}
        inverted = copy.deepcopy(valid)
        inverted["aeRange"] = {"minFps": rate(30), "maxFps": rate(15)}
        point = copy.deepcopy(valid)
        point["aeRange"] = {"minFps": rate(24), "maxFps": rate(24)}
        ranged_fixed = copy.deepcopy(valid)
        ranged_fixed["mechanism"] = "fixed_ae"
        manual_rate = copy.deepcopy(valid)
        manual_rate["manualTiming"] = {"confirmed": False, "frameRate": rate(24)}
        missing_manual = copy.deepcopy(valid)
        missing_manual["mechanism"] = "manual"
        float_rate = copy.deepcopy(valid)
        float_rate["aeRange"]["maxFps"] = {"numerator": 30.0, "denominator": 1}
        extra = copy.deepcopy(valid)
        extra["note"] = "device probe"
        bad_phase = copy.deepcopy(valid)
        bad_phase["phase"] = "P010"
        bool_exposure = copy.deepcopy(valid)
        bool_exposure["exposureNs"] = True
        assigned_without_rate = copy.deepcopy(valid)
        assigned_without_rate["containerTimestamps"] = {"assigned": True, "rate": None}
        cases = (
            None,
            [],
            {},
            extra,
            unreduced,
            inverted,
            point,
            ranged_fixed,
            manual_rate,
            missing_manual,
            float_rate,
            bad_phase,
            bool_exposure,
            assigned_without_rate,
        )
        for sample in cases:
            with self.subTest(sample=type(sample).__name__):
                with self.assertRaises(ValueError):
                    validate_policy(sample)
        with self.assertRaises(ValueError):
            assess_policy(valid, mutant="copy-jpeg-size")
        with self.assertRaises(ValueError):
            retain_ae_upper({"numerator": 30, "denominator": 1}, {"numerator": 24, "denominator": 2})


if __name__ == "__main__":
    unittest.main()
