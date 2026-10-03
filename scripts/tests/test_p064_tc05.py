"""TC-P064-05 unconsented clipping."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p064_tc05", Path(__file__).resolve().parents[1] / "gates" / "p064_tc05.py"
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
        "sampleId": "highlight-r",
        "locus": "highlight",
        "outsideDomain": True,
        "clippingPermission": False,
        "silentClamp": False,
        "claimsFullRange": False,
        "affectedCount": 0,
    }
    base.update(overrides)
    return base


class TcP06405(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P064-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_packet_strings(self):
        self.assertEqual(
            _MODULE.NEGATIVE,
            "Silently clamping highlights while claiming full retained range must fail.",
        )
        self.assertIn("negative channels", _MODULE.REPEAT)
        self.assertIn("extreme exposure", _MODULE.REPEAT)

    def test_unconsented_highlight_requests_a_policy(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "policy_required")
        self.assertEqual(result["rejectedClaims"], ["unconsented-out-of-domain"])
        self.assertIn("highlight-r", result["preservedResults"])
        self.assertIn("affected-count:0", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_silent_clamp_claiming_full_range_fails(self):
        result = evaluate(
            payload(silentClamp=True, claimsFullRange=True, clippingPermission=True, affectedCount=4)
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["silent-clamp-full-range"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("highlight-r", result["preservedResults"])
        self.assertIn("locus:highlight", result["preservedResults"])
        self.assertIn("affected-count:4", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "clipped_recorded", "policy_required"})

    def test_authorized_clip_records_the_count(self):
        result = evaluate(payload(clippingPermission=True, affectedCount=4))
        self.assertEqual(result["decision"], "clipped_recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("affected-count:4", result["preservedResults"])
        self.assertIn("highlight-r", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_repeat_negative_channel(self):
        result = evaluate(payload(sampleId="neg-g", locus="negative-channel"))
        self.assertEqual(result["decision"], "policy_required")
        self.assertIn("neg-g", result["preservedResults"])
        self.assertIn("locus:negative-channel", result["preservedResults"])

    def test_repeat_saturated_color(self):
        result = evaluate(
            payload(sampleId="sat-b", locus="saturated-color", clippingPermission=True, affectedCount=2)
        )
        self.assertEqual(result["decision"], "clipped_recorded")
        self.assertIn("locus:saturated-color", result["preservedResults"])
        self.assertIn("affected-count:2", result["preservedResults"])

    def test_repeat_extreme_exposure(self):
        result = evaluate(payload(sampleId="exp", locus="extreme-exposure", silentClamp=True, claimsFullRange=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("silent-clamp-full-range", result["rejectedClaims"])
        self.assertIn("locus:extreme-exposure", result["preservedResults"])
        self.assertIn("exp", result["preservedResults"])

    def test_inside_domain_is_withheld(self):
        result = evaluate(
            payload(sampleId="mid", locus="inside", outsideDomain=False, affectedCount=0)
        )
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("mid", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "locus": "inside", "outsideDomain": True},
            {**valid, "affectedCount": -1},
            {**valid, "silentClamp": "yes"},
            {**valid, "sampleId": ""},
            {**valid, "locus": "black"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
