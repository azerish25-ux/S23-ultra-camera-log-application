"""TC-P054-05 false-detail enhancement."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p054_tc05", Path(__file__).resolve().parents[1] / "gates" / "p054_tc05.py"
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
        "acutance": "1",
        "ringing": False,
        "falseColor": False,
        "textureLoss": False,
        "acutanceOnly": False,
    }
    base.update(overrides)
    return base


class TcP05405(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P054-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])
        self.assertIn(result["preservedResults"][0], result["preservedResults"])

    def test_negative_acutance_alone_does_not_certify_detail(self):
        result = evaluate(payload(subject="fabric", acutance="3", acutanceOnly=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["acutance-only"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("acutance:3", result["preservedResults"])
        self.assertIn("fabric", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "reported"})

    def test_repeat_fabric_reports_ringing(self):
        result = evaluate(payload(subject="fabric", acutance="2.2", ringing=True))
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], ["ringing"])
        self.assertIn("fabric", result["preservedResults"])
        self.assertIn("acutance:2.2", result["preservedResults"])

    def test_repeat_diagonal_reports_false_color(self):
        result = evaluate(payload(subject="diagonal", acutance="1.8", falseColor=True))
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], ["false-color"])
        self.assertIn("diagonal", result["preservedResults"])

    def test_repeat_point_light_reports_texture_loss(self):
        result = evaluate(payload(subject="point-light", acutance="2", textureLoss=True))
        self.assertEqual(result["decision"], "withheld")
        self.assertIn("texture-loss", result["rejectedClaims"])
        self.assertIn("point-light", result["preservedResults"])

    def test_repeat_low_light_hair_reports_each_artifact(self):
        result = evaluate(
            payload(
                subject="low-light-hair",
                acutance="2.5",
                ringing=True,
                falseColor=True,
                textureLoss=True,
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], ["ringing", "false-color", "texture-loss"])
        self.assertIn("low-light-hair", result["preservedResults"])
        self.assertIn("acutance:2.5", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_clean_subject_is_reported_not_upgraded(self):
        result = evaluate(payload(subject="diagonal", acutance="0.4"))
        self.assertEqual(result["decision"], "reported")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("diagonal", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "subject"},
            {**valid, "extra": True},
            {**valid, "subject": "hair"},
            {**valid, "acutance": "2.20"},
            {**valid, "ringing": "yes"},
            {**valid, "falseColor": 1},
            {**valid, "acutanceOnly": None},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
