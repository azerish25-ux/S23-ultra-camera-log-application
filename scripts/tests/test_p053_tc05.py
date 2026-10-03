"""TC-P053-05 false-detail enhancement."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p053_tc05", Path(__file__).resolve().parents[1] / "gates" / "p053_tc05.py"
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
        "acutance": "10",
        "ringing": False,
        "falseColor": False,
        "textureLoss": False,
        "edgeContrastOnly": False,
    }
    base.update(overrides)
    return base


class TcP05305(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P053-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_fabric_without_artifacts_is_still_not_recovered_detail(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("subject:fabric", result["preservedResults"])
        self.assertIn("acutance:10", result["preservedResults"])
        self.assertIn("acutance is not recovered detail", result["openQuestions"])

    def test_diagonal_lines_report_ringing_separately(self):
        result = evaluate(payload(subject="diagonal-lines", acutance="80", ringing=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], ["ringing"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("subject:diagonal-lines", result["preservedResults"])
        self.assertIn("acutance:80", result["preservedResults"])

    def test_point_lights_and_hair_report_each_artifact(self):
        lights = evaluate(payload(subject="point-lights", falseColor=True, textureLoss=True, acutance="40"))
        hair = evaluate(payload(subject="low-light-hair", textureLoss=True, acutance="12"))
        self.assertEqual(lights["decision"], "withheld")
        self.assertEqual(lights["rejectedClaims"], ["false-color", "texture-loss"])
        self.assertIn("subject:point-lights", lights["preservedResults"])
        self.assertEqual(hair["decision"], "withheld")
        self.assertEqual(hair["rejectedClaims"], ["texture-loss"])
        self.assertIn("subject:low-light-hair", hair["preservedResults"])
        self.assertNotIn(lights["decision"], {"qualified", "allowed"})

    def test_acutance_alone_does_not_certify_detail(self):
        result = evaluate(payload(subject="fabric", acutance="99", edgeContrastOnly=True, ringing=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["acutance-only", "ringing"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("subject:fabric", result["preservedResults"])
        self.assertIn("acutance:99", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "withheld"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {**valid, "subject": "brick"},
            {**valid, "acutance": "10.0"},
            {**valid, "ringing": 1},
            {**valid, "edgeContrastOnly": "yes"},
            {key: value for key, value in valid.items() if key != "subject"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
