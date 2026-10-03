"""TC-P056-03 border policy, corners, and halo support."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p056_tc03", Path(__file__).resolve().parents[1] / "gates" / "p056_tc03.py"
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
        "borderPolicy": "replicate",
        "readOutside": False,
        "haloIgnored": False,
        "staleRead": False,
        "discontinuity": False,
        "support": 2,
    }
    base.update(overrides)
    return base


class TcP05603(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P056-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_corner_tl_applies_the_border_policy(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "border-applied")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("site:corner-tl", result["preservedResults"])
        self.assertIn("policy:replicate", result["preservedResults"])
        self.assertIn("support:2", result["preservedResults"])

    def test_corner_tr_and_remaining_corners(self):
        for site in ("corner-tr", "corner-bl", "corner-br"):
            result = evaluate(payload(site=site, borderPolicy="mirror"))
            self.assertEqual(result["decision"], "border-applied")
            self.assertIn(f"site:{site}", result["preservedResults"])
            self.assertIn("policy:mirror", result["preservedResults"])

    def test_kernel_support_boundary(self):
        result = evaluate(payload(site="kernel-boundary", support=1, borderPolicy="constant"))
        self.assertEqual(result["decision"], "border-applied")
        self.assertIn("site:kernel-boundary", result["preservedResults"])
        self.assertIn("support:1", result["preservedResults"])

    def test_negative_outside_retained_rows(self):
        result = evaluate(payload(site="row-buffer", readOutside=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("outside-retained-rows", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("site:row-buffer", result["preservedResults"])

    def test_ignored_halo_and_stale_read_fail_separately(self):
        halo = evaluate(payload(site="tile-seam", haloIgnored=True))
        stale = evaluate(payload(site="tile-seam", staleRead=True))
        self.assertEqual(halo["rejectedClaims"], ["ignored-halo"])
        self.assertEqual(stale["rejectedClaims"], ["stale-read"])
        self.assertIn("site:tile-seam", halo["preservedResults"])
        self.assertNotIn(halo["decision"], {"qualified", "allowed"})

    def test_missing_support_and_discontinuity_fail(self):
        missing = evaluate(payload(support=0))
        self.assertIn("missing-support", missing["rejectedClaims"])
        broken = evaluate(payload(discontinuity=True))
        self.assertEqual(broken["rejectedClaims"], ["discontinuity"])
        self.assertIn("support:2", broken["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "site": "center"},
            {**valid, "borderPolicy": "wrap"},
            {**valid, "readOutside": "no"},
            {**valid, "support": -1},
            {k: v for k, v in valid.items() if k != "support"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
