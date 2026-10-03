"""TC-P060-05 unconsented clipping."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p060_tc05", Path(__file__).resolve().parents[1] / "gates" / "p060_tc05.py"
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
        "domain": "limited-10",
        "channel": "Y",
        "value": "1023",
        "clippingPermission": False,
        "claimFullRange": False,
        "locus": "highlight",
    }
    base.update(overrides)
    return base


class TcP06005(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P060-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.EXPECTED, result["reasons"])
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])

    def test_packet_strings(self):
        self.assertIn("full retained range", _MODULE.NEGATIVE)
        self.assertIn("negative channels", _MODULE.REPEAT)

    def test_unconsented_highlight_is_rejected_unclamped(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["unconsented-clip"])
        self.assertIn("value:1023", result["preservedResults"])
        self.assertIn("stored:1023", result["preservedResults"])
        self.assertIn("affected:0", result["preservedResults"])
        self.assertNotIn("clamped:940", result["preservedResults"])

    def test_silent_full_range_claim_fails(self):
        result = evaluate(payload(clippingPermission=True, claimFullRange=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("silent-full-range-claim", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("affected:1", result["preservedResults"])
        self.assertIn("stored:1023", result["preservedResults"])
        self.assertIn("clamped:940", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "clipped"})

    def test_authorized_clip_records_the_count(self):
        result = evaluate(payload(clippingPermission=True))
        self.assertEqual(result["decision"], "clipped")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("affected:1", result["preservedResults"])
        self.assertIn("clamped:940", result["preservedResults"])

    def test_repeat_negative_channel(self):
        result = evaluate(
            payload(domain="scene-linear", channel="G", value="-0.2", locus="negative")
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("value:-0.2", result["preservedResults"])
        self.assertIn("stored:-0.2", result["preservedResults"])
        self.assertIn("channel:G", result["preservedResults"])

    def test_repeat_saturated_color(self):
        result = evaluate(
            payload(domain="scene-linear", channel="R", value="1.4", locus="saturated", clippingPermission=True)
        )
        self.assertEqual(result["decision"], "clipped")
        self.assertIn("affected:1", result["preservedResults"])
        self.assertIn("clamped:1", result["preservedResults"])
        self.assertIn("value:1.4", result["preservedResults"])

    def test_repeat_extreme_exposure(self):
        result = evaluate(
            payload(domain="scene-linear", channel="B", value="8", locus="extreme-exposure")
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("value:8", result["preservedResults"])
        self.assertIn("affected:0", result["preservedResults"])

    def test_inside_value_is_retained(self):
        result = evaluate(payload(value="64", locus="inside"))
        self.assertEqual(result["decision"], "retained")
        self.assertIn("stored:64", result["preservedResults"])
        self.assertIn("affected:0", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {**valid, "value": "1.5"},
            {**valid, "locus": "inside"},
            {**valid, "channel": "R"},
            {**valid, "clippingPermission": "yes"},
            {k: v for k, v in valid.items() if k != "value"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
