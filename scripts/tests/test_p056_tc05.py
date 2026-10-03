"""TC-P056-05 acutance does not certify recovered detail."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p056_tc05", Path(__file__).resolve().parents[1] / "gates" / "p056_tc05.py"
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
        "subject": "fabric",
        "acutance": "1.4",
        "ringing": False,
        "falseColor": False,
        "textureLoss": False,
    }
    base.update(overrides)
    return base


class TcP05605(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P056-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["decision"], "withheld")
        self.assertTrue(result["reasons"])

    def test_high_acutance_on_fabric_does_not_certify_detail(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["rejectedClaims"], ["acutance-not-recovered-detail"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("subject:fabric", result["preservedResults"])
        self.assertIn("acutance:1.4", result["preservedResults"])

    def test_diagonal_lines_report_ringing_separately(self):
        result = evaluate(payload(subject="diagonal-lines", ringing=True, acutance="0.4"))
        self.assertContract(result)
        self.assertEqual(result["rejectedClaims"], ["ringing"])
        self.assertIn("subject:diagonal-lines", result["preservedResults"])
        self.assertNotIn("acutance-not-recovered-detail", result["rejectedClaims"])

    def test_point_lights_report_false_color_and_acutance_apart(self):
        result = evaluate(payload(subject="point-lights", falseColor=True, acutance="2"))
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], ["false-color", "acutance-not-recovered-detail"])
        self.assertIn("subject:point-lights", result["preservedResults"])

    def test_low_light_hair_reports_texture_loss(self):
        result = evaluate(payload(subject="low-light-hair", textureLoss=True, acutance="0.2"))
        self.assertEqual(result["rejectedClaims"], ["texture-loss"])
        self.assertIn("texture-loss:true", result["preservedResults"])
        self.assertIn("subject:low-light-hair", result["preservedResults"])

    def test_low_acutance_without_artifacts_stays_withheld(self):
        result = evaluate(payload(acutance="0.2"))
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "subject": "sky"},
            {**valid, "acutance": "1.40"},
            {**valid, "ringing": 1},
            {k: v for k, v in valid.items() if k != "falseColor"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
