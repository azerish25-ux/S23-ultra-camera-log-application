"""TC-P063-05 unconsented clipping."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p063_tc05", Path(__file__).resolve().parents[1] / "gates" / "p063_tc05.py"
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
        "sampleId": "highlight",
        "channel": "R",
        "value": "4",
        "domainFloor": "0",
        "domainCeiling": "1",
        "clippingPermitted": False,
        "silentClamp": True,
        "claimsFullRange": True,
        "affectedCount": "0",
        "locus": "highlight",
    }
    base.update(overrides)
    return base


class TcP06305(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P063-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_packet_strings(self):
        self.assertEqual(
            _MODULE.NEGATIVE,
            "Silently clamping highlights while claiming full retained range must fail.",
        )

    def test_silent_clamp_claiming_full_range_fails(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["silent-clamp-full-range"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("value:4", result["preservedResults"])
        self.assertIn("highlight", result["preservedResults"])
        self.assertIn("affected:0", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "clip_recorded"})

    def test_repeat_negative_channel(self):
        result = evaluate(
            payload(
                sampleId="neg-g",
                channel="G",
                value="-0.4",
                locus="negative",
                silentClamp=False,
                claimsFullRange=False,
            )
        )
        self.assertEqual(result["decision"], "policy_required")
        self.assertEqual(result["rejectedClaims"], ["unconsented-out-of-domain"])
        self.assertIn("value:-0.4", result["preservedResults"])
        self.assertIn("channel:G", result["preservedResults"])
        self.assertIn("an explicit clipping policy is required", result["openQuestions"])

    def test_repeat_saturated_color(self):
        result = evaluate(
            payload(
                sampleId="sat-b",
                channel="B",
                value="1.4",
                locus="saturated",
                silentClamp=False,
                claimsFullRange=False,
            )
        )
        self.assertEqual(result["decision"], "policy_required")
        self.assertIn("value:1.4", result["preservedResults"])
        self.assertIn("locus:saturated", result["preservedResults"])

    def test_repeat_extreme_exposure_records_count_when_authorized(self):
        result = evaluate(
            payload(
                sampleId="hot",
                value="18",
                locus="extreme-exposure",
                silentClamp=False,
                claimsFullRange=False,
                clippingPermitted=True,
                affectedCount="6",
            )
        )
        self.assertEqual(result["decision"], "clip_recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("affected:6", result["preservedResults"])
        self.assertIn("value:18", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_in_domain_is_not_qualification(self):
        result = evaluate(
            payload(value="0.5", silentClamp=False, claimsFullRange=False, locus="highlight")
        )
        self.assertEqual(result["decision"], "in_domain")
        self.assertIn("value:0.5", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "value": "-0"},
            {**valid, "domainFloor": "1", "domainCeiling": "0"},
            {**valid, "affectedCount": "01"},
            {**valid, "channel": "Y"},
            {**valid, "silentClamp": "yes"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
