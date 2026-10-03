"""TC-P048-05 training error alone does not cover a held-out scene."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p048_tc05", Path(__file__).resolve().parents[1] / "gates" / "p048_tc05.py"
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


class TcP04805(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P048-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_constants(self):
        self.assertIn("training patches", _MODULE.INTERVENTION)
        self.assertIn("training and validation", _MODULE.EXPECTED)
        self.assertIn("only training error", _MODULE.NEGATIVE)

    def test_negative_training_only_report_keeps_validation(self):
        result = evaluate(
            payload(reportTrainingOnly=True, scene="skin", validationError="40", trainingError="2")
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("training-only-report", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("validation-error:40", result["preservedResults"])
        self.assertIn("training-error:2", result["preservedResults"])
        self.assertIn("scene:skin", result["preservedResults"])

    def test_repeat_skin_restricts_profile(self):
        result = evaluate(payload(scene="skin", validationError="40", trainingError="2", supported=False))
        self.assertContract(result)
        self.assertEqual(result["decision"], "restricted")
        self.assertIn("held-out-failure", result["rejectedClaims"])
        self.assertIn("scene:skin", result["preservedResults"])
        self.assertIn("validation-error:40", result["preservedResults"])

    def test_repeat_foliage_and_narrow_band(self):
        foliage = evaluate(payload(scene="foliage", validationError="11", trainingError="1"))
        narrow = evaluate(payload(scene="narrow_band", validationError="9", trainingError="1"))
        self.assertEqual(foliage["decision"], "restricted")
        self.assertIn("scene:foliage", foliage["preservedResults"])
        self.assertEqual(narrow["decision"], "restricted")
        self.assertIn("scene:narrow_band", narrow["preservedResults"])
        self.assertNotIn(foliage["decision"], {"qualified", "allowed"})
        self.assertNotIn(narrow["decision"], {"qualified", "allowed"})

    def test_chart_agreement_stays_separate_from_held_out_scenes(self):
        result = evaluate(payload())
        self.assertEqual(result["decision"], "training_separated")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("training-error:2", result["preservedResults"])
        self.assertIn("validation-error:2", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        for item in (None, {}, {**valid, "scene": "studio"}, {**valid, "trainingError": "2.0"}):
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
