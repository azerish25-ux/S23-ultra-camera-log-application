"""TC-P061-05 unconsented clipping."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p061_tc05", Path(__file__).resolve().parents[1] / "gates" / "p061_tc05.py"
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
        "value": "4",
        "floor": "0",
        "ceiling": "1",
        "clippingPermitted": False,
        "claimFullRetainedRange": True,
        "affectedCount": 0,
        "locus": "highlight",
    }
    base.update(overrides)
    return base


class TcP06105(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P061-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_packet_strings(self):
        self.assertIn("without clipping permission", _MODULE.INTERVENTION)
        self.assertEqual(
            _MODULE.NEGATIVE,
            "Silently clamping highlights while claiming full retained range must fail.",
        )
        self.assertIn("negative channels", _MODULE.REPEAT)
        self.assertIn("extreme exposure", _MODULE.REPEAT)

    def test_silent_highlight_clamp_claim_fails(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(
            result["rejectedClaims"],
            ["silent-clamp-full-range", "unconsented-clip"],
        )
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("value:4", result["preservedResults"])
        self.assertIn("domain:0..1", result["preservedResults"])
        self.assertIn("explicit clipping policy required", result["openQuestions"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "retained"})

    def test_authorized_clip_records_the_count(self):
        result = evaluate(
            payload(clippingPermitted=True, claimFullRetainedRange=False, affectedCount=3)
        )
        self.assertEqual(result["decision"], "clip_recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("affected:3", result["preservedResults"])
        self.assertIn("value:4", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_repeat_negative_channel(self):
        result = evaluate(
            payload(
                value="-0.2",
                locus="negative-channel",
                claimFullRetainedRange=False,
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("unconsented-clip", result["rejectedClaims"])
        self.assertIn("value:-0.2", result["preservedResults"])
        self.assertIn("locus:negative-channel", result["preservedResults"])

    def test_repeat_saturated_color(self):
        result = evaluate(payload(value="2", locus="saturated", claimFullRetainedRange=False))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("value:2", result["preservedResults"])
        self.assertIn("locus:saturated", result["preservedResults"])
        self.assertNotIn("silent-clamp-full-range", result["rejectedClaims"])

    def test_repeat_extreme_exposure(self):
        result = evaluate(
            payload(
                value="16",
                locus="extreme-exposure",
                clippingPermitted=True,
                claimFullRetainedRange=True,
                affectedCount=9,
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("silent-clamp-full-range", result["rejectedClaims"])
        self.assertIn("value:16", result["preservedResults"])
        self.assertIn("affected:9", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "clip_recorded"})

    def test_inside_value_is_retained(self):
        result = evaluate(
            payload(
                value="0.5",
                locus="inside",
                claimFullRetainedRange=False,
                clippingPermitted=False,
                affectedCount=0,
            )
        )
        self.assertEqual(result["decision"], "retained")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("value:0.5", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "value": "4.0"},
            {**valid, "clippingPermitted": "no"},
            {**valid, "affectedCount": -1},
            {**valid, "locus": "inside"},
            {**valid, "floor": "1", "ceiling": "0", "locus": "inside", "value": "0"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
