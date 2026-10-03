"""TC-P059-05 unconsented clipping."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p059_tc05", Path(__file__).resolve().parents[1] / "gates" / "p059_tc05.py"
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
        "channel": "y",
        "value": "0.18",
        "domainMin": "0",
        "domainMax": "1",
        "clippingPermitted": False,
        "silentClamp": False,
        "claimsFullRange": False,
        "affectedCount": 0,
        "repeat": "none",
    }
    base.update(overrides)
    return base


class TcP05905(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P059-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("channel:y", result["preservedResults"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_constants_encode_the_case(self):
        self.assertIn("clipping permission", _MODULE.INTERVENTION)
        self.assertIn("affected counts", _MODULE.EXPECTED)
        self.assertIn("Silently clamping", _MODULE.NEGATIVE)

    def test_in_domain_value_is_withheld(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("value:0.18", result["preservedResults"])
        self.assertIn("domain:0..1", result["preservedResults"])

    def test_negative_silent_clamp_claiming_full_range_fails(self):
        result = evaluate(
            payload(value="1.2", silentClamp=True, claimsFullRange=True, clippingPermitted=True, affectedCount=3)
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "clip_recorded"})
        self.assertEqual(result["rejectedClaims"], ["silent-clamp-full-range"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("value:1.2", result["preservedResults"])
        self.assertNotIn("value:1", result["preservedResults"])

    def test_unconsented_highlight_requests_a_policy(self):
        result = evaluate(payload(value="1.2"))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["unconsented-clip"])
        self.assertIn("value:1.2", result["preservedResults"])
        self.assertIn("explicit clipping policy required", result["openQuestions"])

    def test_repeat_negative_channel(self):
        result = evaluate(payload(channel="blue", value="-0.2", repeat="negative-channel"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("value:-0.2", result["preservedResults"])
        self.assertIn("repeat:negative-channel", result["preservedResults"])
        self.assertIn("channel:blue", result["preservedResults"])
        self.assertIn("unconsented-clip", result["rejectedClaims"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_repeat_saturated_color(self):
        result = evaluate(payload(channel="red", value="1.4", repeat="saturated-color"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("value:1.4", result["preservedResults"])
        self.assertIn("repeat:saturated-color", result["preservedResults"])
        self.assertIn("domain:0..1", result["preservedResults"])

    def test_repeat_extreme_exposure_records_authorized_clipping(self):
        result = evaluate(
            payload(
                value="8",
                clippingPermitted=True,
                affectedCount=12,
                repeat="extreme-exposure",
            )
        )
        self.assertEqual(result["decision"], "clip_recorded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("value:8", result["preservedResults"])
        self.assertIn("affected-count:12", result["preservedResults"])
        self.assertIn("repeat:extreme-exposure", result["preservedResults"])

    def test_authorized_clip_without_a_count_is_rejected(self):
        result = evaluate(payload(value="1.2", clippingPermitted=True, affectedCount=0))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["missing-affected-count"])
        self.assertIn("value:1.2", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "value"},
            {**valid, "extra": True},
            {**valid, "value": "1.20"},
            {**valid, "value": "-0"},
            {**valid, "domainMin": "1", "domainMax": "1"},
            {**valid, "channel": "Y"},
            {**valid, "affectedCount": -1},
            {**valid, "silentClamp": 1},
            {**valid, "repeat": "shadow"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
