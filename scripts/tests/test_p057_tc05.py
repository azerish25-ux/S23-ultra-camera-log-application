"""TC-P057-05 unconsented clipping does not retain a full-range claim."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p057_tc05", Path(__file__).resolve().parents[1] / "gates" / "p057_tc05.py"
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
        "kind": "highlight",
        "value": "1.4",
        "domainMin": "0",
        "domainMax": "1",
        "clippingPermitted": False,
        "silentClamp": False,
        "claimsFullRange": False,
    }
    base.update(overrides)
    return base


class TcP05705(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P057-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_unconsented_highlight_requests_a_policy(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["unconsented-clip"])
        self.assertIn("value:1.4", result["preservedResults"])
        self.assertIn("affected:unrecorded", result["preservedResults"])
        self.assertTrue(any("explicit clipping policy required" in item for item in result["openQuestions"]))

    def test_repeat_negative_channel(self):
        result = evaluate(payload(kind="negative-channel", value="-0.2"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("kind:negative-channel", result["preservedResults"])
        self.assertIn("value:-0.2", result["preservedResults"])

    def test_repeat_saturated_color_and_extreme_exposure(self):
        for kind, value in (("saturated-color", "1.8"), ("extreme-exposure", "16")):
            result = evaluate(payload(kind=kind, value=value))
            self.assertEqual(result["decision"], "rejected")
            self.assertIn(f"kind:{kind}", result["preservedResults"])
            self.assertIn(f"value:{value}", result["preservedResults"])
            self.assertNotIn(result["decision"], {"qualified", "allowed", "clip_recorded"})

    def test_silent_clamp_claiming_full_range_fails(self):
        result = evaluate(payload(silentClamp=True, claimsFullRange=True, clippingPermitted=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["silent-clamp-full-range"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("value:1.4", result["preservedResults"])
        self.assertIn("affected:hidden", result["preservedResults"])

    def test_authorized_clip_records_the_affected_count(self):
        result = evaluate(payload(kind="extreme-exposure", value="16", clippingPermitted=True))
        self.assertEqual(result["decision"], "clip_recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("affected:1", result["preservedResults"])
        self.assertIn("value:16", result["preservedResults"])
        self.assertIn("clamped-to:1", result["preservedResults"])

    def test_in_range_value_is_withheld(self):
        result = evaluate(payload(kind="highlight", value="0.5"))
        self.assertEqual(result["decision"], "withheld")
        self.assertIn("affected:0", result["preservedResults"])
        self.assertIn("value:0.5", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {**valid, "value": "1.40"},
            {**valid, "kind": "shadow"},
            {**valid, "domainMin": "1", "domainMax": "0"},
            {**valid, "silentClamp": "no"},
            {k: v for k, v in valid.items() if k != "value"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
