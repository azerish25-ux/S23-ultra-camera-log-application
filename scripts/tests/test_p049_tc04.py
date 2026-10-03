"""TC-P049-04 operation order across an encoding boundary is rejected."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p049_tc04", Path(__file__).resolve().parents[1] / "gates" / "p049_tc04.py"
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
        "operation": "exposure-scale",
        "movedAcrossEncoding": False,
        "plausible": True,
    }
    base.update(overrides)
    return base


class TcP04904(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P049-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_constants(self):
        self.assertIn("encoding boundary", _MODULE.INTERVENTION)
        self.assertIn("domain-specific reference", _MODULE.EXPECTED)
        self.assertIn("visually plausible", _MODULE.NEGATIVE)

    def test_logarithmic_move_is_rejected_even_when_plausible(self):
        result = evaluate(
            payload(domain="logarithmic", operation="reduction", movedAcrossEncoding=True)
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["order-violation", "reduction-across-logarithmic"])
        self.assertIn("domain:logarithmic", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertTrue(any("plausible" in item for item in result["reasons"]))

    def test_display_encoded_blur_is_rejected(self):
        result = evaluate(
            payload(domain="display-encoded", operation="blur", movedAcrossEncoding=True, plausible=False)
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("blur-across-display-encoded", result["rejectedClaims"])
        self.assertIn("domain:display-encoded", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "order_held"})

    def test_scene_linear_color_stays_in_order_when_not_moved(self):
        result = evaluate(payload(domain="scene-linear", operation="color"))
        self.assertEqual(result["decision"], "order_held")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("operation:color", result["preservedResults"])
        self.assertTrue(any("agrees" in item for item in result["reasons"]))

    def test_scene_linear_move_is_still_rejected(self):
        result = evaluate(payload(movedAcrossEncoding=True, plausible=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("exposure-scale-across-scene-linear", result["rejectedClaims"])
        self.assertIn("plausible:true", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "domain": "linear"},
            {**valid, "operation": "sharpen"},
            {**valid, "plausible": "yes"},
            {k: v for k, v in valid.items() if k != "domain"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
