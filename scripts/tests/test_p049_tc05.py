"""TC-P049-05 acutance alone does not certify recovered detail."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p049_tc05", Path(__file__).resolve().parents[1] / "gates" / "p049_tc05.py"
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
        "acutance": "900",
        "ringing": False,
        "falseColor": False,
        "textureLoss": False,
        "certifyFromAcutance": False,
    }
    base.update(overrides)
    return base


class TcP04905(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P049-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn("acutance:900", result["preservedResults"])

    def test_constants(self):
        self.assertIn("sharpness", _MODULE.INTERVENTION)
        self.assertIn("edge contrast", _MODULE.EXPECTED)
        self.assertIn("acutance", _MODULE.NEGATIVE)

    def test_fabric_reports_ringing_and_texture_loss_separately(self):
        result = evaluate(payload(ringing=True, textureLoss=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], ["ringing", "texture-loss"])
        self.assertIn("artifact:ringing", result["preservedResults"])
        self.assertIn("artifact:texture-loss", result["preservedResults"])
        self.assertIn("subject:fabric", result["preservedResults"])

    def test_diagonal_lines_report_false_color_alone(self):
        result = evaluate(payload(subject="diagonal-lines", falseColor=True))
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], ["false-color"])
        self.assertIn("subject:diagonal-lines", result["preservedResults"])

    def test_point_lights_do_not_upgrade_on_acutance(self):
        result = evaluate(payload(subject="point-lights", ringing=True, certifyFromAcutance=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["acutance-only", "ringing"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("acutance:900", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "withheld"})

    def test_low_light_hair_withholds_without_artifacts(self):
        result = evaluate(payload(subject="low-light-hair"))
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("subject:low-light-hair", result["preservedResults"])
        self.assertTrue(any("not recovered detail" in item for item in result["reasons"]))

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "subject": "sky"},
            {**valid, "acutance": "0"},
            {**valid, "acutance": "090"},
            {**valid, "ringing": "yes"},
            {k: v for k, v in valid.items() if k != "subject"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
