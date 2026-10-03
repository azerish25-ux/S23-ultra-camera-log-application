"""TC-P052-04 nonlinear processing order."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p052_tc04", Path(__file__).resolve().parents[1] / "gates" / "p052_tc04.py"
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
        "domain": "scene-linear",
        "operation": "blur",
        "declaredOrder": "before-encode",
        "appliedOrder": "before-encode",
        "visuallyPlausible": False,
        "disagreement": "0",
    }
    base.update(overrides)
    return base


class TcP05204(unittest.TestCase):
    def test_scene_linear_order_is_not_qualification(self):
        result = evaluate(payload())
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P052-04")
        self.assertEqual(result["decision"], "ordered")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("domain:scene-linear", result["preservedResults"])
        self.assertIn("disagreement:0", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_negative_plausible_reorder_keeps_disagreement(self):
        result = evaluate(
            payload(
                domain="display-encoded",
                operation="exposure-scale",
                appliedOrder="after-encode",
                visuallyPlausible=True,
                disagreement="0.4",
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("order-violation", result["rejectedClaims"])
        self.assertIn("plausible-insufficient", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("disagreement:0.4", result["preservedResults"])
        self.assertIn("operation:exposure-scale", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "ordered"})

    def test_repeat_logarithmic(self):
        result = evaluate(payload(domain="logarithmic", operation="reduction"))
        self.assertEqual(result["decision"], "ordered")
        self.assertIn("domain:logarithmic", result["preservedResults"])
        self.assertIn("operation:reduction", result["preservedResults"])

    def test_repeat_display_encoded_disagreement(self):
        result = evaluate(payload(domain="display-encoded", operation="color", disagreement="0.2"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("domain-disagreement", result["rejectedClaims"])
        self.assertIn("disagreement:0.2", result["preservedResults"])
        self.assertIn("domain:display-encoded", result["preservedResults"])

    def test_repeat_scene_linear_blur(self):
        result = evaluate(payload(domain="scene-linear", operation="blur"))
        self.assertEqual(result["decision"], "ordered")
        self.assertIn("declared:before-encode", result["preservedResults"])
        self.assertIn("applied:before-encode", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "domain"},
            {**valid, "extra": True},
            {**valid, "domain": "video"},
            {**valid, "visuallyPlausible": "true"},
            {**valid, "disagreement": "0.20"},
            {**valid, "appliedOrder": "during"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
