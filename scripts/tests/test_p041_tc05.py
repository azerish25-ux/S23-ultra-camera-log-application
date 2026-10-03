"""TC-P041-05 held-out scene failure."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p041_tc05", Path(__file__).resolve().parents[1] / "gates" / "p041_tc05.py"
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
        "scene": "chart",
        "trainingError": "0.01",
        "validationError": "0.01",
        "reportTrainingOnly": False,
        "supportedConditions": ["chart"],
    }
    base.update(overrides)
    return base


class TcP04105(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P041-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_training_only_report_fails_and_keeps_both_slots(self):
        result = evaluate(payload(reportTrainingOnly=True, validationError="0.2", scene="skin"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["training-only-error"])
        self.assertIn("training:0.01", result["preservedResults"])
        self.assertIn("validation:0.2", result["preservedResults"])
        self.assertIn("scene:skin", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertNotEqual(result["preservedResults"].count("training:0.01"), 0)

    def test_omitted_validation_is_not_replaced_by_training_error(self):
        result = evaluate(payload(validationError="omitted"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("validation:omitted", result["preservedResults"])
        self.assertIn("training:0.01", result["preservedResults"])
        self.assertNotIn("validation:0.01", result["preservedResults"])

    def test_skin_repeat_restricts_the_profile(self):
        result = evaluate(
            payload(scene="skin", trainingError="0.01", validationError="0.08", supportedConditions=["chart"])
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "restricted")
        self.assertEqual(result["rejectedClaims"], ["held-out:skin"])
        self.assertIn("training:0.01", result["preservedResults"])
        self.assertIn("validation:0.08", result["preservedResults"])
        self.assertIn("supported:chart", result["preservedResults"])
        self.assertIn("skin is outside the supported conditions", result["openQuestions"])

    def test_saturated_fabric_repeat_keeps_errors_separate(self):
        result = evaluate(
            payload(scene="fabric", trainingError="0.02", validationError="0.11", supportedConditions=["fabric"])
        )
        self.assertEqual(result["decision"], "restricted")
        self.assertIn("scene:fabric", result["preservedResults"])
        self.assertIn("training:0.02", result["preservedResults"])
        self.assertIn("validation:0.11", result["preservedResults"])
        self.assertLess(
            result["preservedResults"].index("training:0.02"),
            result["preservedResults"].index("validation:0.11"),
        )

    def test_foliage_repeat_is_restricted(self):
        result = evaluate(payload(scene="foliage", validationError="0.05", supportedConditions=["chart", "foliage"]))
        self.assertEqual(result["decision"], "restricted")
        self.assertEqual(result["rejectedClaims"], ["held-out:foliage"])
        self.assertIn("supported:foliage", result["preservedResults"])
        self.assertIn("supported:chart", result["preservedResults"])

    def test_narrow_band_lighting_repeat_is_restricted(self):
        result = evaluate(
            payload(scene="narrow-band", validationError="0.2", trainingError="0.015", supportedConditions=[])
        )
        self.assertEqual(result["decision"], "restricted")
        self.assertIn("held-out:narrow-band", result["rejectedClaims"])
        self.assertIn("scene:narrow-band", result["preservedResults"])
        self.assertIn("validation:0.2", result["preservedResults"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_matching_held_out_error_is_checked_not_qualified(self):
        result = evaluate(payload(scene="chart", validationError="0.009", trainingError="0.01"))
        self.assertEqual(result["decision"], "held_out_checked")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("training:0.01", result["preservedResults"])
        self.assertIn("validation:0.009", result["preservedResults"])
        self.assertIn("training and validation stay separate", result["openQuestions"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "scene": "sky"},
            {**valid, "trainingError": "-0.01"},
            {**valid, "validationError": "0.010"},
            {**valid, "reportTrainingOnly": "false"},
            {**valid, "supportedConditions": ["skin", "skin"]},
            {**valid, "supportedConditions": ["lab"]},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
