"""TC-P050-05 acutance does not certify recovered detail."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p050_tc05", Path(__file__).resolve().parents[1] / "gates" / "p050_tc05.py"
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
        "ringing": False,
        "falseColor": False,
        "textureLoss": False,
        "acutance": 80,
        "claimUpgrade": False,
    }
    base.update(overrides)
    return base


class TcP05005(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P050-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertTrue(any(item.startswith("subject:") for item in result["preservedResults"]))

    def test_constants(self):
        self.assertIn("false color", _MODULE.INTERVENTION)
        self.assertIn("each artifact separately", _MODULE.EXPECTED)
        self.assertIn("acutance score", _MODULE.NEGATIVE)

    def test_repeat_subjects_without_upgrade(self):
        for subject in ("fabric", "diagonal", "point_light", "hair"):
            result = evaluate(payload(subject=subject, acutance=120))
            self.assertContract(result)
            self.assertEqual(result["decision"], "inspected")
            self.assertEqual(result["rejectedClaims"], [])
            self.assertIn(f"subject:{subject}", result["preservedResults"])
            self.assertIn("acutance:120", result["preservedResults"])
            self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_artifacts_are_reported_separately(self):
        result = evaluate(
            payload(subject="diagonal", ringing=True, falseColor=True, textureLoss=True, acutance=900)
        )
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], ["ringing", "false-color", "texture-loss"])
        self.assertIn("artifact:ringing", result["reasons"])
        self.assertIn("artifact:false-color", result["reasons"])
        self.assertIn("artifact:texture-loss", result["reasons"])
        self.assertIn("subject:diagonal", result["preservedResults"])
        self.assertIn("acutance:900", result["preservedResults"])

    def test_high_acutance_alone_does_not_certify(self):
        result = evaluate(payload(subject="hair", acutance=990, claimUpgrade=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "inspected"})
        self.assertIn("acutance-only", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("subject:hair", result["preservedResults"])
        self.assertIn("acutance:990", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "subject": "sky"},
            {**valid, "acutance": -1},
            {**valid, "ringing": 1},
            {k: v for k, v in valid.items() if k != "claimUpgrade"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
