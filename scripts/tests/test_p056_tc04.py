"""TC-P056-04 encoded-domain operation order is rejected."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p056_tc04", Path(__file__).resolve().parents[1] / "gates" / "p056_tc04.py"
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
        "operation": "reduction",
        "domain": "scene-linear",
        "order": "before-encoding",
        "matchesReference": True,
        "visuallyPlausible": True,
    }
    base.update(overrides)
    return base


class TcP05604(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P056-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_scene_linear_before_encoding_is_kept(self):
        for operation in ("reduction", "blur", "exposure", "color"):
            result = evaluate(payload(operation=operation))
            self.assertContract(result)
            self.assertEqual(result["decision"], "order-kept")
            self.assertEqual(result["rejectedClaims"], [])
            self.assertIn(f"operation:{operation}", result["preservedResults"])
            self.assertIn("domain:scene-linear", result["preservedResults"])

    def test_logarithmic_after_encoding_is_rejected_even_if_plausible(self):
        result = evaluate(
            payload(domain="logarithmic", order="after-encoding", visuallyPlausible=True)
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("encoded-domain-order", result["rejectedClaims"])
        self.assertIn("plausible-but-illegal-order", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("domain:logarithmic", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "order-kept"})

    def test_display_encoded_fixture_is_rejected(self):
        result = evaluate(
            payload(domain="display-encoded", order="before-encoding", visuallyPlausible=False)
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("encoded-domain-order", result["rejectedClaims"])
        self.assertNotIn("plausible-but-illegal-order", result["rejectedClaims"])
        self.assertIn("domain:display-encoded", result["preservedResults"])

    def test_scene_linear_reference_mismatch_is_rejected(self):
        result = evaluate(payload(matchesReference=False, visuallyPlausible=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("reference-disagreement", result["rejectedClaims"])
        self.assertIn("plausible-but-illegal-order", result["rejectedClaims"])
        self.assertIn("order:before-encoding", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {**valid, "operation": "sharpen"},
            {**valid, "domain": "logc"},
            {**valid, "order": "during"},
            {**valid, "matchesReference": "yes"},
            {k: v for k, v in valid.items() if k != "order"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
