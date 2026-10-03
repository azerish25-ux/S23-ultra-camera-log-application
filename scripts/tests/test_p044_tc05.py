"""TC-P044-05 held-out scene failure."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p044_tc05", Path(__file__).resolve().parents[1] / "gates" / "p044_tc05.py"
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
        "trainingError": "2",
        "validationError": "2",
        "scene": "chart",
        "reportTrainingOnly": False,
        "supported": True,
    }
    base.update(overrides)
    return base


class TcP04405(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P044-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_constants_encode_intervention_expected_and_negative(self):
        self.assertIn("training patches", _MODULE.INTERVENTION)
        self.assertIn("training and validation", _MODULE.EXPECTED)
        self.assertIn("only training error", _MODULE.NEGATIVE)

    def test_chart_agreement_stays_separate_from_a_natural_scene(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "training_separated")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("training-error:2", result["preservedResults"])
        self.assertIn("validation-error:2", result["preservedResults"])
        self.assertIn("scene:chart", result["preservedResults"])

    def test_skin_repeat_restricts_the_profile(self):
        result = evaluate(payload(scene="skin", validationError="40", supported=False))
        self.assertEqual(result["decision"], "restricted")
        self.assertEqual(result["rejectedClaims"], ["held-out-failure"])
        self.assertIn("training-error:2", result["preservedResults"])
        self.assertIn("validation-error:40", result["preservedResults"])
        self.assertIn("scene:skin", result["preservedResults"])
        self.assertIn("profile restricted; skin is outside supported conditions", result["openQuestions"])

    def test_foliage_repeat_keeps_both_errors(self):
        result = evaluate(payload(scene="foliage", trainingError="1", validationError="15"))
        self.assertEqual(result["decision"], "restricted")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("training-error:1", result["preservedResults"])
        self.assertIn("validation-error:15", result["preservedResults"])
        self.assertIn("scene:foliage", result["preservedResults"])

    def test_saturated_fabric_and_narrow_band_repeats(self):
        fabric = evaluate(payload(scene="fabric", validationError="9"))
        narrow = evaluate(payload(scene="narrow_band", validationError="11", trainingError="0"))
        self.assertEqual(fabric["decision"], "restricted")
        self.assertEqual(narrow["decision"], "restricted")
        self.assertIn("scene:fabric", fabric["preservedResults"])
        self.assertIn("scene:narrow_band", narrow["preservedResults"])
        self.assertIn("validation-error:11", narrow["preservedResults"])
        self.assertIn("training-error:0", narrow["preservedResults"])

    def test_negative_training_only_report_cannot_qualify(self):
        result = evaluate(
            payload(scene="skin", validationError="40", reportTrainingOnly=True, supported=True)
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "restricted"})
        self.assertEqual(result["rejectedClaims"], ["training-only-report"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("training-error:2", result["preservedResults"])
        self.assertIn("validation-error:40", result["preservedResults"])
        self.assertIn("scene:skin", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "scene"},
            {**valid, "extra": True},
            {**valid, "scene": "sky"},
            {**valid, "trainingError": "02"},
            {**valid, "validationError": -1},
            {**valid, "reportTrainingOnly": "false"},
            {**valid, "supported": 1},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
