"""TC-P062-05 unconsented clipping."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p062_tc05", Path(__file__).resolve().parents[1] / "gates" / "p062_tc05.py"
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
        "sampleId": "hi",
        "channel": "R",
        "value": "1.8",
        "locus": "highlight",
        "domainFloor": "0",
        "domainCeiling": "1",
        "clippingPermitted": False,
        "silentClamp": False,
        "claimsFullRange": False,
    }
    base.update(overrides)
    return base


class TcP06205(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P062-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_packet_strings(self):
        self.assertEqual(
            _MODULE.NEGATIVE,
            "Silently clamping highlights while claiming full retained range must fail.",
        )

    def test_unconsented_highlight_requests_a_policy(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["clipping-policy-required"])
        self.assertIn("value:1.8", result["preservedResults"])
        self.assertIn("affected:0", result["preservedResults"])
        self.assertIn("domain:0..1", result["preservedResults"])
        self.assertIn("hi", result["preservedResults"])
        self.assertIn("explicit clipping policy required", result["openQuestions"])

    def test_silent_full_range_claim_fails(self):
        result = evaluate(payload(silentClamp=True, claimsFullRange=True, clippingPermitted=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["silent-clamp-full-range"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("value:1.8", result["preservedResults"])
        self.assertIn("affected:0", result["preservedResults"])
        self.assertIn("full-range-claim:yes", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "clipped_recorded"})

    def test_authorized_clip_records_the_affected_count(self):
        result = evaluate(payload(clippingPermitted=True))
        self.assertEqual(result["decision"], "clipped_recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("affected:1", result["preservedResults"])
        self.assertIn("value:1.8", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_repeat_negative_channel(self):
        result = evaluate(payload(sampleId="neg", channel="G", value="-0.2", locus="negative"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("value:-0.2", result["preservedResults"])
        self.assertIn("channel:G", result["preservedResults"])
        self.assertIn("locus:negative", result["preservedResults"])
        self.assertIn("affected:0", result["preservedResults"])

    def test_repeat_saturated_color(self):
        result = evaluate(
            payload(sampleId="sat", channel="B", value="1.4", locus="saturated", clippingPermitted=True)
        )
        self.assertEqual(result["decision"], "clipped_recorded")
        self.assertIn("value:1.4", result["preservedResults"])
        self.assertIn("affected:1", result["preservedResults"])
        self.assertIn("locus:saturated", result["preservedResults"])

    def test_repeat_extreme_exposure(self):
        result = evaluate(
            payload(sampleId="hot", value="8", locus="extreme-exposure", silentClamp=True, claimsFullRange=True)
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("value:8", result["preservedResults"])
        self.assertIn("locus:extreme-exposure", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_inside_domain_is_retained(self):
        result = evaluate(payload(sampleId="mid", value="0.4", locus="inside"))
        self.assertEqual(result["decision"], "retained")
        self.assertIn("value:0.4", result["preservedResults"])
        self.assertEqual(result["rejectedClaims"], [])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "value"},
            {**valid, "extra": True},
            {**valid, "value": "1.0"},
            {**valid, "value": "-0"},
            {**valid, "locus": "inside"},
            {**valid, "clippingPermitted": "false"},
            {**valid, "domainFloor": "1", "domainCeiling": "0"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
