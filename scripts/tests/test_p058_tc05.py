"""TC-P058-05 unconsented clipping."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p058_tc05", Path(__file__).resolve().parents[1] / "gates" / "p058_tc05.py"
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
        "domainMin": "0",
        "domainMax": "1",
        "sample": "0.18",
        "channel": "mid",
        "clippingPermitted": False,
        "silentClamp": False,
        "claimsFullRange": False,
        "affectedCount": 0,
    }
    base.update(overrides)
    return base


class TcP05805(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P058-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn("domain:0..1", result["preservedResults"])

    def test_inside_sample_is_not_qualified(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "inside_domain")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("sample:0.18", result["preservedResults"])

    def test_negative_silent_clamp_claiming_full_range_fails(self):
        result = evaluate(
            payload(channel="highlight", sample="1.4", silentClamp=True, claimsFullRange=True, affectedCount=4)
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("silent-clamp-full-range", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("sample:1.4", result["preservedResults"])
        self.assertIn("affected:4", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_repeat_negative_channel(self):
        result = evaluate(payload(channel="negative", sample="-0.2"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("unconsented-out-of-domain", result["rejectedClaims"])
        self.assertIn("sample:-0.2", result["preservedResults"])
        self.assertIn("channel:negative", result["preservedResults"])
        self.assertIn("explicit clipping policy required", result["openQuestions"])

    def test_repeat_saturated_color_and_extreme_exposure(self):
        saturated = evaluate(payload(channel="saturated", sample="1.5"))
        self.assertEqual(saturated["decision"], "rejected")
        self.assertIn("sample:1.5", saturated["preservedResults"])
        self.assertIn("channel:saturated", saturated["preservedResults"])
        exposure = evaluate(payload(channel="exposure", sample="16"))
        self.assertEqual(exposure["decision"], "rejected")
        self.assertIn("unconsented-out-of-domain", exposure["rejectedClaims"])
        self.assertIn("sample:16", exposure["preservedResults"])
        self.assertTrue(any("extreme exposure" in item for item in exposure["reasons"]))

    def test_authorized_clip_records_the_affected_count(self):
        result = evaluate(
            payload(channel="highlight", sample="1.2", clippingPermitted=True, affectedCount=3)
        )
        self.assertEqual(result["decision"], "clip_recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("affected:3", result["preservedResults"])
        self.assertIn("sample:1.2", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "sample"},
            {**valid, "extra": True},
            {**valid, "sample": "0.180"},
            {**valid, "domainMin": "1", "domainMax": "0"},
            {**valid, "channel": "shadow"},
            {**valid, "affectedCount": -1},
            {**valid, "silentClamp": "false"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
