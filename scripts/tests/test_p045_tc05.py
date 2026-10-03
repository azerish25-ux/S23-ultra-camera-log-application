"""TC-P045-05 held-out scene failure."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p045_tc05", Path(__file__).resolve().parents[1] / "gates" / "p045_tc05.py"
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
        "profileId": "fit-1",
        "scene": "chart",
        "illuminant": "training",
        "trainingError": "0.01",
        "validationError": "0.01",
        "trainingOnlyReport": False,
    }
    base.update(overrides)
    return base


class TcP04505(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P045-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn("training-error:0.01", result["preservedResults"])

    def test_separated_chart_errors_are_not_a_measured_profile(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "separated")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("validation-error:0.01", result["preservedResults"])
        self.assertIn("profile:fit-1", result["preservedResults"])

    def test_negative_training_only_report_keeps_validation_error(self):
        result = evaluate(
            payload(scene="skin", illuminant="independent", validationError="0.4", trainingOnlyReport=True)
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("training-only-report", result["rejectedClaims"])
        self.assertIn("withheld-validation:skin", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("training-error:0.01", result["preservedResults"])
        self.assertIn("validation-error:0.4", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "restricted"})

    def test_repeat_skin(self):
        result = evaluate(payload(scene="skin", illuminant="independent", validationError="0.33"))
        self.assertEqual(result["decision"], "restricted")
        self.assertIn("validation:skin", result["rejectedClaims"])
        self.assertIn("independent-illuminant", result["rejectedClaims"])
        self.assertIn("training-error:0.01", result["preservedResults"])
        self.assertIn("validation-error:0.33", result["preservedResults"])

    def test_repeat_saturated_fabric(self):
        result = evaluate(payload(scene="saturated_fabric", illuminant="independent", validationError="0.5"))
        self.assertEqual(result["decision"], "restricted")
        self.assertIn("validation:saturated_fabric", result["rejectedClaims"])
        self.assertIn("scene:saturated_fabric", result["preservedResults"])
        self.assertIn("validation-error:0.5", result["preservedResults"])

    def test_repeat_foliage(self):
        result = evaluate(payload(scene="foliage", illuminant="independent", validationError="0.22"))
        self.assertEqual(result["decision"], "restricted")
        self.assertIn("validation:foliage", result["rejectedClaims"])
        self.assertIn("illuminant:independent", result["preservedResults"])

    def test_repeat_narrow_band_lighting(self):
        result = evaluate(payload(scene="narrow_band", illuminant="independent", validationError="0.8"))
        self.assertEqual(result["decision"], "restricted")
        self.assertIn("validation:narrow_band", result["rejectedClaims"])
        self.assertIn("validation-error:0.8", result["preservedResults"])
        self.assertNotEqual(result["preservedResults"].index("training-error:0.01"),
                            result["preservedResults"].index("validation-error:0.8"))

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "scene"},
            {**valid, "extra": True},
            {**valid, "scene": "sky"},
            {**valid, "trainingOnlyReport": "false"},
            {**valid, "trainingError": "0.010"},
            {**valid, "validationError": "-0.1"},
            {**valid, "illuminant": "A"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
