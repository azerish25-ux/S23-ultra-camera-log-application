"""TC-P052-01 negative and bright intermediate values."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p052_tc01", Path(__file__).resolve().parents[1] / "gates" / "p052_tc01.py"
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
        "sampleId": "s0",
        "locus": "around-zero",
        "value": "-0.05",
        "stored": "-0.05",
        "unitClamped": False,
        "storageLimit": "4",
        "displayLimit": "1",
    }
    base.update(overrides)
    return base


class TcP05201(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P052-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn("value:-0.05", result["preservedResults"])

    def test_around_zero_negative_is_preserved(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "preserved")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("stored:-0.05", result["preservedResults"])
        self.assertIn("locus:around-zero", result["preservedResults"])

    def test_negative_unit_clamp_keeps_the_signed_value(self):
        result = evaluate(payload(value="-0.2", stored="0", unitClamped=True))
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("implicit-unit-clamp", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("value:-0.2", result["preservedResults"])
        self.assertIn("stored:0", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "preserved"})

    def test_repeat_source_white_keeps_over_range(self):
        result = evaluate(payload(locus="source-white", value="2.5", stored="2.5"))
        self.assertEqual(result["decision"], "preserved")
        self.assertIn("value:2.5", result["preservedResults"])
        self.assertIn("locus:source-white", result["preservedResults"])
        self.assertIn("display-limit:1", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_repeat_encoding_boundary_clips_only_at_storage(self):
        result = evaluate(payload(locus="encoding-boundary", value="4.5", stored="4"))
        self.assertEqual(result["decision"], "preserved")
        self.assertIn("value:4.5", result["preservedResults"])
        self.assertIn("expected:4", result["preservedResults"])
        self.assertIn("storage-limit:4", result["preservedResults"])

    def test_early_display_clamp_is_not_the_storage_limit(self):
        result = evaluate(
            payload(locus="source-white", value="2.5", stored="0.8", displayLimit="0.8")
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("early-display-clamp", result["rejectedClaims"])
        self.assertIn("value:2.5", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "value"},
            {**valid, "extra": True},
            {**valid, "locus": "mid"},
            {**valid, "unitClamped": "false"},
            {**valid, "value": "0.050"},
            {**valid, "stored": "-0"},
            {**valid, "storageLimit": "0"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
