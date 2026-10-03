"""TC-P055-01 negative and bright intermediate values."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p055_tc01", Path(__file__).resolve().parents[1] / "gates" / "p055_tc01.py"
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
        "sampleId": "sat-g",
        "channel": "G",
        "value": "-1.8",
        "locus": "below-black",
        "implicitClamp": False,
        "declaredLimit": "storage",
        "storageFloor": "-8",
        "storageCeiling": "16",
    }
    base.update(overrides)
    return base


class TcP05501(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P055-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_packet_strings(self):
        self.assertEqual(
            _MODULE.INTERVENTION,
            "Exercise values below black and highlights above diffuse white through the phase boundary.",
        )
        self.assertEqual(
            _MODULE.NEGATIVE,
            "An implicit zero-to-one clamp must be detected.",
        )

    def test_below_black_is_retained(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "retained")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("value:-1.8", result["preservedResults"])
        self.assertIn("sat-g", result["preservedResults"])

    def test_highlight_above_white_is_retained(self):
        result = evaluate(payload(sampleId="sat-r", channel="R", value="4", locus="above-white"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "retained")
        self.assertIn("value:4", result["preservedResults"])
        self.assertIn("channel:R", result["preservedResults"])

    def test_negative_implicit_clamp_is_rejected(self):
        result = evaluate(payload(implicitClamp=True, value="4", locus="above-white", channel="R"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["implicit-zero-to-one-clamp"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("value:4", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "retained"})

    def test_repeat_around_zero(self):
        result = evaluate(payload(sampleId="near-zero", value="-0.001", locus="around-zero"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "retained")
        self.assertIn("value:-0.001", result["preservedResults"])
        self.assertIn("locus:around-zero", result["preservedResults"])

    def test_repeat_source_white_reference(self):
        result = evaluate(payload(sampleId="white", channel="R", value="1", locus="source-white"))
        self.assertEqual(result["decision"], "retained")
        self.assertIn("value:1", result["preservedResults"])
        self.assertIn("locus:source-white", result["preservedResults"])

    def test_repeat_encoding_boundary(self):
        result = evaluate(
            payload(sampleId="ceiling", channel="R", value="16", locus="encoding-boundary")
        )
        self.assertEqual(result["decision"], "retained")
        self.assertIn("value:16", result["preservedResults"])
        self.assertIn("storage:-8..16", result["preservedResults"])

    def test_explicit_display_limit_is_not_an_implicit_clamp(self):
        result = evaluate(payload(value="4", locus="above-white", declaredLimit="display", channel="R"))
        self.assertEqual(result["decision"], "bounded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("value:4", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "rejected"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "value"},
            {**valid, "extra": True},
            {**valid, "implicitClamp": "true"},
            {**valid, "value": "4.0"},
            {**valid, "locus": "black"},
            {**valid, "declaredLimit": "file"},
            {**valid, "channel": "A"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
