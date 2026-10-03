"""TC-P043-05 held-out scene failure."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p043_tc05", Path(__file__).resolve().parents[1] / "gates" / "p043_tc05.py"
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


def payload(**overrides):
    base = {
        "profileId": "profile-a",
        "scene": "skin",
        "trainingError": "0.02",
        "validationError": "0.2",
        "reportTrainingOnly": False,
        "supported": True,
    }
    base.update(overrides)
    return base


class TcP04305(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P043-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn("profile:profile-a", result["preservedResults"])
        self.assertIn("training:0.02", result["preservedResults"])

    def test_training_only_report_fails_and_keeps_validation(self):
        result = evaluate(payload(reportTrainingOnly=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "restricted", "separated"})
        self.assertIn("training-only", result["rejectedClaims"])
        self.assertIn("skin", result["rejectedClaims"])
        self.assertIn("validation:skin:0.2", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_skin_holdout_restricts_the_profile(self):
        result = evaluate(payload(scene="skin"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "restricted")
        self.assertIn("skin", result["rejectedClaims"])
        self.assertIn("support-not-restricted", result["rejectedClaims"])
        self.assertIn("validation:skin:0.2", result["preservedResults"])
        self.assertIn("training:0.02", result["preservedResults"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_saturated_fabrics_stay_separate_from_training(self):
        result = evaluate(payload(scene="saturated-fabrics", supported=False))
        self.assertEqual(result["decision"], "restricted")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("saturated-fabrics", result["rejectedClaims"])
        self.assertNotIn("support-not-restricted", result["rejectedClaims"])
        self.assertIn("validation:saturated-fabrics:0.2", result["preservedResults"])
        self.assertIn("training:0.02", result["preservedResults"])

    def test_foliage_holdout_is_restricted(self):
        result = evaluate(payload(scene="foliage", supported=False))
        self.assertEqual(result["decision"], "restricted")
        self.assertEqual(result["rejectedClaims"], ["foliage"])
        self.assertIn("validation:foliage:0.2", result["preservedResults"])

    def test_narrow_band_lighting_is_restricted(self):
        result = evaluate(payload(scene="narrow-band", supported=False))
        self.assertEqual(result["decision"], "restricted")
        self.assertIn("narrow-band", result["rejectedClaims"])
        self.assertIn("profile:profile-a", result["preservedResults"])
        self.assertIn("training 0.02 kept separate from validation 0.2", result["reasons"])

    def test_agreeing_errors_are_separated_not_qualified(self):
        result = evaluate(payload(validationError="0.02"))
        self.assertEqual(result["decision"], "separated")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("training:0.02", result["preservedResults"])
        self.assertIn("validation:skin:0.02", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "scene": "sky"},
            {**valid, "trainingError": "0.020"},
            {**valid, "reportTrainingOnly": "false"},
            {**valid, "profileId": ""},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
