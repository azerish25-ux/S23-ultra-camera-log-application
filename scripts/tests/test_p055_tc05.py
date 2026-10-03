"""TC-P055-05 false-detail enhancement."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p055_tc05", Path(__file__).resolve().parents[1] / "gates" / "p055_tc05.py"
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
        "acutance": "0.8",
        "ringing": False,
        "falseColor": False,
        "textureLoss": False,
        "edgeContrastOnly": False,
    }
    base.update(overrides)
    return base


class TcP05505(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P055-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_packet_strings(self):
        self.assertEqual(
            _MODULE.NEGATIVE,
            "A high acutance score alone must not certify recovered detail.",
        )
        self.assertIn("false color", _MODULE.INTERVENTION)

    def test_clean_record_is_not_a_quality_upgrade(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("subject:fabric", result["preservedResults"])
        self.assertIn("acutance:0.8", result["preservedResults"])

    def test_negative_acutance_alone_is_withheld(self):
        result = evaluate(payload(acutance="2.5", edgeContrastOnly=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], ["acutance-only"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("acutance:2.5", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "recorded"})

    def test_repeat_fabric_reports_artifacts_separately(self):
        result = evaluate(payload(ringing=True, falseColor=True, textureLoss=True))
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], ["ringing", "false-color", "texture-loss"])
        self.assertIn("subject:fabric", result["preservedResults"])
        self.assertTrue(any("artifact ringing" in item for item in result["reasons"]))
        self.assertTrue(any("artifact false-color" in item for item in result["reasons"]))
        self.assertTrue(any("artifact texture-loss" in item for item in result["reasons"]))

    def test_repeat_diagonal_lines(self):
        result = evaluate(payload(subject="diagonal-lines", ringing=True, acutance="1.2"))
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], ["ringing"])
        self.assertIn("subject:diagonal-lines", result["preservedResults"])
        self.assertIn("acutance:1.2", result["preservedResults"])

    def test_repeat_point_lights_and_hair(self):
        lights = evaluate(payload(subject="point-lights", falseColor=True))
        hair = evaluate(payload(subject="low-light-hair", textureLoss=True, edgeContrastOnly=True))
        self.assertIn("false-color", lights["rejectedClaims"])
        self.assertIn("subject:point-lights", lights["preservedResults"])
        self.assertEqual(hair["decision"], "withheld")
        self.assertEqual(hair["rejectedClaims"], ["texture-loss", "acutance-only"])
        self.assertIn("subject:low-light-hair", hair["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {**valid, "subject": "sky"},
            {**valid, "acutance": "0.80"},
            {**valid, "ringing": 1},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
