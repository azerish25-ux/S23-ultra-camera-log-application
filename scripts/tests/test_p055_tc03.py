"""TC-P055-03 boundary and halo support."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p055_tc03", Path(__file__).resolve().parents[1] / "gates" / "p055_tc03.py"
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
        "site": "corner-tl",
        "feature": "impulse",
        "borderPolicy": "documented-replicate",
        "readOutside": False,
        "haloIgnored": False,
        "retainedRows": 8,
        "requiredHalo": 2,
        "sampleValue": "1.5",
    }
    base.update(overrides)
    return base


class TcP05503(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P055-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.EXPECTED, result["reasons"])
        self.assertTrue(result["reasons"])

    def test_packet_strings(self):
        self.assertEqual(
            _MODULE.NEGATIVE,
            "Reading outside retained rows or ignoring required halos must fail.",
        )
        self.assertIn("row-buffer limit", _MODULE.INTERVENTION)

    def test_documented_policy_applies_at_corner(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "border_applied")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("site:corner-tl", result["preservedResults"])
        self.assertIn("value:1.5", result["preservedResults"])
        self.assertIn("policy:documented-replicate", result["preservedResults"])

    def test_repeat_second_corner(self):
        result = evaluate(payload(site="corner-br", feature="edge", sampleValue="-0.25"))
        self.assertEqual(result["decision"], "border_applied")
        self.assertIn("site:corner-br", result["preservedResults"])
        self.assertIn("value:-0.25", result["preservedResults"])

    def test_repeat_kernel_support_boundary(self):
        result = evaluate(payload(site="kernel-support", retainedRows=3, requiredHalo=3))
        self.assertEqual(result["decision"], "border_applied")
        self.assertIn("site:kernel-support", result["preservedResults"])
        self.assertIn("halo:3", result["preservedResults"])

    def test_negative_outside_rows_fails(self):
        result = evaluate(payload(readOutside=True, site="row-buffer"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("outside-retained-rows", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("value:1.5", result["preservedResults"])
        self.assertIn("site:row-buffer", result["preservedResults"])

    def test_negative_ignored_halo_fails(self):
        result = evaluate(payload(haloIgnored=True, site="tile-seam"))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["ignored-halo"])
        self.assertIn("site:tile-seam", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "border_applied"})

    def test_missing_support_is_rejected(self):
        result = evaluate(payload(retainedRows=2, requiredHalo=4, site="edge"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("missing-support", result["rejectedClaims"])
        self.assertIn("rows:2", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {**valid, "site": "middle"},
            {**valid, "readOutside": "yes"},
            {**valid, "retainedRows": 0},
            {**valid, "sampleValue": "1.50"},
            {**valid, "borderPolicy": "clamp"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
