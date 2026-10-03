"""TC-P011-08 a short cold run is not unlimited recording."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p011_tc08", Path(__file__).resolve().parents[1] / "gates" / "p011_tc08.py"
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def rate(numerator=15, denominator=1):
    return {"numerator": numerator, "denominator": denominator}


def payload(**overrides):
    base = {
        "durationSec": 30,
        "requiredEnduranceSec": 600,
        "thermalWarm": False,
        "lensId": "wide",
        "audioSelection": "internal-mic",
        "environmentalEvidence": False,
        "advertisedSize": "3840x2160",
        "aeMin": rate(15),
        "aeMax": rate(30),
        "requestedFps": rate(24),
        "containerTimestampsAssigned": True,
    }
    base.update(overrides)
    return base


class TcP01108(unittest.TestCase):
    def assert_contract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P011-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "unlimited", "native_fixed_24"})
        self.assertTrue(result["reasons"])

    def test_encodes_intervention_expected_and_negative(self):
        self.assertIn("short successful physical take", _MODULE.INTERVENTION)
        self.assertIn("unqualified", _MODULE.EXPECTED)
        self.assertIn("unlimited recording", _MODULE.NEGATIVE)

    def test_short_cold_run_does_not_extrapolate(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "slice_only")
        self.assertIn("unlimited-extrapolation", result["rejectedClaims"])
        self.assertIn("native-fixed-24", result["rejectedClaims"])
        self.assertEqual(result["openQuestions"], ["endurance unqualified"])
        self.assertIn("30s", result["preservedResults"])
        self.assertIn("wide", result["preservedResults"])
        self.assertIn("internal-mic", result["preservedResults"])
        self.assertIn("3840x2160", result["preservedResults"])
        self.assertIn("ae:15/1-30/1", result["preservedResults"])
        self.assertTrue(any("does not extrapolate" in item for item in result["reasons"]))
        self.assertTrue(any("physical S23" in item for item in result["reasons"]))

    def test_thermal_warmup_still_leaves_a_short_slice_unqualified(self):
        result = evaluate(payload(thermalWarm=True, environmentalEvidence=False))
        self.assertEqual(result["decision"], "slice_only")
        self.assertNotIn("unlimited-extrapolation", result["rejectedClaims"])
        self.assertIn("endurance unqualified", result["openQuestions"])
        self.assertIn("30s", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "unlimited"})

    def test_different_lens_and_audio_keep_their_identities(self):
        result = evaluate(
            payload(
                lensId="telephoto",
                audioSelection="usb-lav",
                durationSec=45,
                containerTimestampsAssigned=False,
            )
        )
        self.assertEqual(result["decision"], "slice_only")
        self.assertIn("45s", result["preservedResults"])
        self.assertIn("telephoto", result["preservedResults"])
        self.assertIn("usb-lav", result["preservedResults"])
        self.assertIn("requested:24/1", result["preservedResults"])
        self.assertEqual(result["rejectedClaims"], ["unlimited-extrapolation"])

    def test_met_endurance_is_observed_not_unlimited_or_qualified(self):
        result = evaluate(
            payload(
                durationSec=600,
                requiredEnduranceSec=600,
                thermalWarm=True,
                environmentalEvidence=True,
                containerTimestampsAssigned=False,
            )
        )
        self.assertEqual(result["decision"], "endurance_observed")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "unlimited"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["openQuestions"], [])
        self.assertIn("600s", result["preservedResults"])
        self.assertTrue(any("not an unlimited recording claim" in item for item in result["reasons"]))
        self.assertTrue(any("does not qualify a physical S23" in item for item in result["reasons"]))

    def test_missing_environment_blocks_endurance_even_after_the_duration(self):
        result = evaluate(
            payload(
                durationSec=900,
                thermalWarm=True,
                environmentalEvidence=False,
                containerTimestampsAssigned=False,
            )
        )
        self.assertEqual(result["decision"], "slice_only")
        self.assertIn("endurance unqualified", result["openQuestions"])
        self.assertIn("900s", result["preservedResults"])
        self.assertNotIn("unlimited-extrapolation", result["rejectedClaims"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {**valid, "durationSec": -1},
            {**valid, "requiredEnduranceSec": 0},
            {**valid, "thermalWarm": "yes"},
            {**valid, "lensId": ""},
            {**valid, "advertisedSize": "3840x"},
            {**valid, "aeMin": {"numerator": True, "denominator": 1}},
            {**valid, "durationSec": float("nan")},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
