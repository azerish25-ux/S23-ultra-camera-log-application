"""TC-P049-03 documented border policy rejects outside reads and ignored halos."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p049_tc03", Path(__file__).resolve().parents[1] / "gates" / "p049_tc03.py"
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
        "borderPolicy": "replicate-documented",
        "readOutsideRetained": False,
        "haloIgnored": False,
        "impulse": True,
    }
    base.update(overrides)
    return base


class TcP04903(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P049-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn("support:halo-required", result["preservedResults"])

    def test_constants(self):
        self.assertIn("image boundary", _MODULE.INTERVENTION)
        self.assertIn("border policy", _MODULE.EXPECTED)
        self.assertIn("required halos", _MODULE.NEGATIVE)

    def test_corner_top_left_uses_the_documented_policy(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "border_policy_applied")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("site:corner-tl", result["preservedResults"])
        self.assertIn("impulse:true", result["preservedResults"])

    def test_corner_top_right(self):
        result = evaluate(payload(site="corner-tr"))
        self.assertEqual(result["decision"], "border_policy_applied")
        self.assertIn("site:corner-tr", result["preservedResults"])

    def test_corner_bottom_left(self):
        result = evaluate(payload(site="corner-bl", impulse=False))
        self.assertEqual(result["decision"], "border_policy_applied")
        self.assertIn("site:corner-bl", result["preservedResults"])
        self.assertIn("impulse:false", result["preservedResults"])

    def test_corner_bottom_right(self):
        result = evaluate(payload(site="corner-br"))
        self.assertEqual(result["decision"], "border_policy_applied")
        self.assertIn("site:corner-br", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_kernel_support_boundary(self):
        result = evaluate(payload(site="kernel-boundary"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "border_policy_applied")
        self.assertIn("site:kernel-boundary", result["preservedResults"])

    def test_row_buffer_and_tile_seam_stay_inside_support(self):
        for site in ("row-buffer", "tile-seam"):
            result = evaluate(payload(site=site))
            self.assertEqual(result["decision"], "border_policy_applied")
            self.assertIn(f"site:{site}", result["preservedResults"])

    def test_outside_retained_rows_fail_without_wiping_the_site(self):
        result = evaluate(payload(site="row-buffer", readOutsideRetained=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("outside-retained-rows", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("site:row-buffer", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "border_policy_applied"})

    def test_ignored_halo_fails(self):
        result = evaluate(payload(site="kernel-boundary", haloIgnored=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["ignored-halo"])
        self.assertIn("support:halo-required", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "site": "edge"},
            {**valid, "borderPolicy": "wrap"},
            {**valid, "impulse": 1},
            {k: v for k, v in valid.items() if k != "haloIgnored"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
