"""TC-P050-04 encoded-domain operation order is not visually excused."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p050_tc04", Path(__file__).resolve().parents[1] / "gates" / "p050_tc04.py"
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
        "domain": "scene_linear",
        "operation": "exposure",
        "crossed": False,
        "plausible": False,
        "reference": "scene-linear-exposure",
    }
    base.update(overrides)
    return base


class TcP05004(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P050-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertTrue(any(item.startswith("reference:") for item in result["preservedResults"]))

    def test_constants(self):
        self.assertIn("encoding boundary", _MODULE.INTERVENTION)
        self.assertIn("domain-specific reference", _MODULE.EXPECTED)
        self.assertIn("visually plausible", _MODULE.NEGATIVE)

    def test_repeat_scene_linear_stays_ordered(self):
        for operation in ("reduction", "blur", "exposure", "color"):
            result = evaluate(payload(operation=operation, reference=f"linear-{operation}"))
            self.assertContract(result)
            self.assertEqual(result["decision"], "order_checked")
            self.assertEqual(result["rejectedClaims"], [])
            self.assertIn(f"operation:{operation}", result["preservedResults"])
            self.assertIn(f"reference:linear-{operation}", result["preservedResults"])

    def test_repeat_logarithmic_cross_is_rejected(self):
        result = evaluate(
            payload(
                domain="logarithmic",
                operation="blur",
                crossed=True,
                plausible=True,
                reference="log-blur",
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "order_checked"})
        self.assertIn("order-violation", result["rejectedClaims"])
        self.assertIn("encoded-domain", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertTrue(any("visually plausible" in item for item in result["reasons"]))
        self.assertIn("domain:logarithmic", result["preservedResults"])
        self.assertIn("reference:log-blur", result["preservedResults"])

    def test_repeat_display_encoded_cross_is_rejected(self):
        result = evaluate(
            payload(
                domain="display",
                operation="color",
                crossed=True,
                plausible=True,
                reference="display-color",
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("domain:display", result["preservedResults"])
        self.assertIn("operation:color", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_scene_linear_cross_still_fails(self):
        result = evaluate(payload(crossed=True, plausible=False, operation="reduction"))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["order-violation"])
        self.assertIn("operation:reduction", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "domain": "gamma"},
            {**valid, "operation": "sharpen"},
            {**valid, "crossed": 1},
            {**valid, "reference": "  "},
            {k: v for k, v in valid.items() if k != "plausible"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
