"""TC-P052-05 false-detail enhancement."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p052_tc05", Path(__file__).resolve().parents[1] / "gates" / "p052_tc05.py"
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
        "scene": "fabric",
        "acutance": "0.2",
        "ringing": "0",
        "falseColor": "0",
        "textureLoss": "0",
        "acutanceOnly": False,
    }
    base.update(overrides)
    return base


class TcP05205(unittest.TestCase):
    def test_clean_report_does_not_certify_detail(self):
        result = evaluate(payload())
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P052-05")
        self.assertEqual(result["decision"], "reported")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("acutance:0.2", result["preservedResults"])
        self.assertIn("ringing:0", result["preservedResults"])
        self.assertIn("false-color:0", result["preservedResults"])
        self.assertIn("texture-loss:0", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_negative_acutance_only_keeps_each_artifact(self):
        result = evaluate(
            payload(scene="hair", acutance="0.99", ringing="0.4", falseColor="0.3", textureLoss="0.2", acutanceOnly=True)
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(
            result["rejectedClaims"],
            ["acutance-only", "ringing", "false-color", "texture-loss"],
        )
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("acutance:0.99", result["preservedResults"])
        self.assertIn("ringing:0.4", result["preservedResults"])
        self.assertIn("false-color:0.3", result["preservedResults"])
        self.assertIn("texture-loss:0.2", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "reported"})

    def test_repeat_fabric_withholds_upgrade(self):
        result = evaluate(payload(scene="fabric", acutance="0.9", ringing="0.2"))
        self.assertEqual(result["decision"], "withheld")
        self.assertIn("ringing", result["rejectedClaims"])
        self.assertIn("scene:fabric", result["preservedResults"])
        self.assertIn("acutance:0.9", result["preservedResults"])
        self.assertNotIn("acutance-only", result["rejectedClaims"])

    def test_repeat_diagonal(self):
        result = evaluate(payload(scene="diagonal", falseColor="0.15", acutance="0.8"))
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], ["false-color"])
        self.assertIn("scene:diagonal", result["preservedResults"])
        self.assertIn("false-color:0.15", result["preservedResults"])

    def test_repeat_point_lights(self):
        result = evaluate(payload(scene="point-lights", textureLoss="0.05", ringing="0.04"))
        self.assertEqual(result["decision"], "withheld")
        self.assertIn("ringing", result["rejectedClaims"])
        self.assertIn("texture-loss", result["rejectedClaims"])
        self.assertIn("scene:point-lights", result["preservedResults"])

    def test_repeat_hair(self):
        result = evaluate(payload(scene="hair", acutance="0.7"))
        self.assertEqual(result["decision"], "reported")
        self.assertIn("scene:hair", result["preservedResults"])
        self.assertIn("acutance:0.7", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "scene"},
            {**valid, "extra": True},
            {**valid, "scene": "sky"},
            {**valid, "acutanceOnly": "false"},
            {**valid, "ringing": "0.020"},
            {**valid, "acutance": "-1"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
