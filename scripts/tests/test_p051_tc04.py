"""TC-P051-04 altered operation order is rejected across encodings."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p051_tc04", Path(__file__).resolve().parents[1] / "gates" / "p051_tc04.py"
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
        "declaredPlacement": "before-encoding",
        "actualPlacement": "before-encoding",
        "sample": 8,
        "scale": 2,
        "plausible": False,
    }
    base.update(overrides)
    return base


class TcP05104(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P051-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_constants(self):
        self.assertIn("encoding boundary", _MODULE.INTERVENTION)
        self.assertIn("altered graph", _MODULE.EXPECTED)
        self.assertIn("visually plausible", _MODULE.NEGATIVE)

    def test_repeat_scene_linear_rejects_a_moved_scale_even_when_numbers_match(self):
        result = evaluate(
            payload(
                domain="scene-linear",
                actualPlacement="after-encoding",
                plausible=True,
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["altered-operation-order"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("reference:16", result["preservedResults"])
        self.assertIn("altered:16", result["preservedResults"])
        self.assertIn("sample:8", result["preservedResults"])
        self.assertTrue(any("plausibility" in item for item in result["reasons"]))
        self.assertNotIn(result["decision"], {"qualified", "allowed", "order_accepted"})

    def test_repeat_logarithmic_exposure_disagrees(self):
        result = evaluate(
            payload(domain="logarithmic", actualPlacement="after-encoding", plausible=True)
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("reference:4", result["preservedResults"])
        self.assertIn("altered:6", result["preservedResults"])
        self.assertIn("domain:logarithmic", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_repeat_display_encoded_exposure_disagrees(self):
        result = evaluate(
            payload(domain="display-encoded", actualPlacement="after-encoding", plausible=True)
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("reference:16/17", result["preservedResults"])
        self.assertIn("altered:16/9", result["preservedResults"])
        self.assertIn("domain:display-encoded", result["preservedResults"])

    def test_matching_order_is_accepted_without_qualification(self):
        for domain in ("scene-linear", "logarithmic", "display-encoded"):
            result = evaluate(payload(domain=domain, operation="reduction"))
            self.assertEqual(result["decision"], "order_accepted")
            self.assertEqual(result["rejectedClaims"], [])
            self.assertIn("operation:reduction", result["preservedResults"])
            self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_blur_across_display_encoding_is_rejected(self):
        result = evaluate(
            payload(
                domain="display-encoded",
                operation="blur",
                actualPlacement="after-encoding",
                plausible=True,
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("reference:4/5", result["preservedResults"])
        self.assertIn("altered:4/9", result["preservedResults"])
        self.assertIn("sample:8", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "domain": "video"},
            {**valid, "sample": 6},
            {**valid, "scale": 3},
            {**valid, "plausible": "yes"},
            {k: v for k, v in valid.items() if k != "operation"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
