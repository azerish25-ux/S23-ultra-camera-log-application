"""TC-P051-05 acutance does not certify recovered detail."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p051_tc05", Path(__file__).resolve().parents[1] / "gates" / "p051_tc05.py"
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
        "acutance": 1000,
        "ringing": False,
        "falseColor": False,
        "textureLoss": False,
        "certifyFromAcutance": False,
    }
    base.update(overrides)
    return base


class TcP05105(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P051-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_constants(self):
        self.assertIn("false color", _MODULE.INTERVENTION)
        self.assertIn("edge contrast", _MODULE.EXPECTED)
        self.assertIn("acutance", _MODULE.NEGATIVE)

    def test_high_acutance_alone_does_not_certify(self):
        result = evaluate(payload(acutance=1000))
        self.assertContract(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("acutance:1000", result["preservedResults"])
        self.assertIn("texture:genuine", result["preservedResults"])
        self.assertIn("subject:fabric", result["preservedResults"])
        self.assertIn("edge contrast is not recovered detail", result["openQuestions"])

    def test_artifacts_are_reported_separately(self):
        result = evaluate(payload(ringing=True, falseColor=True, textureLoss=True, acutance=900))
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], ["ringing", "false-color", "texture-loss"])
        self.assertTrue(any("separately" in item for item in result["reasons"]))
        self.assertIn("texture:genuine", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_repeat_diagonal_lines_and_point_lights(self):
        for subject in ("diagonal-lines", "point-lights"):
            result = evaluate(payload(subject=subject, acutance=800))
            self.assertEqual(result["decision"], "withheld")
            self.assertIn(f"subject:{subject}", result["preservedResults"])
            self.assertIn("texture:genuine", result["preservedResults"])

    def test_repeat_low_light_hair(self):
        result = evaluate(payload(subject="low-light-hair", ringing=True, acutance=700))
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], ["ringing"])
        self.assertIn("subject:low-light-hair", result["preservedResults"])
        self.assertIn("acutance:700", result["preservedResults"])

    def test_certify_from_acutance_is_rejected(self):
        result = evaluate(payload(certifyFromAcutance=True, acutance=1000))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("acutance-certified-detail", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("acutance:1000", result["preservedResults"])
        self.assertIn("texture:genuine", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "withheld"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "subject": "sky"},
            {**valid, "acutance": 1001},
            {**valid, "ringing": "yes"},
            {k: v for k, v in valid.items() if k != "falseColor"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
