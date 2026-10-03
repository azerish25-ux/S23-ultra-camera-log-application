"""TC-P056-01 signed and over-range samples are not implicitly clamped."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p056_tc01", Path(__file__).resolve().parents[1] / "gates" / "p056_tc01.py"
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
        "value": "-0.02",
        "boundary": "zero",
        "implicitClamp": False,
        "storageLimit": "none",
    }
    base.update(overrides)
    return base


class TcP05601(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P056-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])

    def test_around_zero_negative_is_preserved(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "preserved")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("s0", result["preservedResults"])
        self.assertIn("value:-0.02", result["preservedResults"])
        self.assertIn("boundary:zero", result["preservedResults"])

    def test_source_white_over_range_is_preserved(self):
        result = evaluate(
            payload(sampleId="white", value="1.25", boundary="source-white", storageLimit="4")
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "preserved")
        self.assertIn("value:1.25", result["preservedResults"])
        self.assertIn("boundary:source-white", result["preservedResults"])
        self.assertIn("limit:4", result["preservedResults"])
        self.assertNotIn("value:1", result["preservedResults"])

    def test_encoding_boundary_respects_the_declared_limit(self):
        result = evaluate(
            payload(sampleId="enc", value="2.5", boundary="encoding-boundary", storageLimit="1.5")
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertIn("beyond-storage-limit", result["rejectedClaims"])
        self.assertIn("value:2.5", result["preservedResults"])
        self.assertIn("enc", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "preserved"})

    def test_negative_implicit_clamp_is_rejected_and_keeps_the_sample(self):
        result = evaluate(payload(implicitClamp=True, value="-0.4"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["implicit-zero-to-one-clamp"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("value:-0.4", result["preservedResults"])
        self.assertNotIn("value:0", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "value"},
            {**valid, "extra": True},
            {**valid, "value": "-0"},
            {**valid, "value": "0.020"},
            {**valid, "boundary": "black"},
            {**valid, "implicitClamp": "true"},
            {**valid, "storageLimit": "0"},
            {**valid, "sampleId": ""},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
