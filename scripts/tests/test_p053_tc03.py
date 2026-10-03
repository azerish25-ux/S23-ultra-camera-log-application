"""TC-P053-03 boundary and halo support."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p053_tc03", Path(__file__).resolve().parents[1] / "gates" / "p053_tc03.py"
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
        "staleRead": False,
        "discontinuity": False,
        "haloSupport": 2,
        "requiredHalo": 2,
    }
    base.update(overrides)
    return base


class TcP05303(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P053-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_corners_apply_the_border_policy(self):
        for site in ("corner-tl", "corner-tr", "corner-bl", "corner-br"):
            result = evaluate(payload(site=site, borderPolicy="mirror"))
            self.assertContract(result)
            self.assertEqual(result["decision"], "border_applied")
            self.assertIn(f"site:{site}", result["preservedResults"])
            self.assertIn("policy:mirror", result["preservedResults"])
            self.assertEqual(result["rejectedClaims"], [])

    def test_kernel_support_boundaries_keep_required_halo(self):
        for site in ("kernel-left", "kernel-right", "kernel-top", "kernel-bottom"):
            result = evaluate(payload(site=site, haloSupport=3, requiredHalo=2, borderPolicy="constant-zero"))
            self.assertEqual(result["decision"], "border_applied")
            self.assertIn(f"site:{site}", result["preservedResults"])
            self.assertIn("halo:3", result["preservedResults"])
            self.assertIn("required-halo:2", result["preservedResults"])

    def test_row_buffer_and_tile_seam_are_separate_sites(self):
        row = evaluate(payload(site="row-buffer"))
        seam = evaluate(payload(site="tile-seam", borderPolicy="replicate"))
        self.assertEqual(row["decision"], "border_applied")
        self.assertEqual(seam["decision"], "border_applied")
        self.assertIn("site:row-buffer", row["preservedResults"])
        self.assertIn("site:tile-seam", seam["preservedResults"])

    def test_reading_outside_retained_rows_fails(self):
        result = evaluate(payload(site="row-buffer", readOutside=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("outside-retained-rows", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("site:row-buffer", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "border_applied"})

    def test_missing_halo_and_stale_read_fail(self):
        halo = evaluate(payload(site="kernel-left", haloSupport=1, requiredHalo=2))
        self.assertEqual(halo["decision"], "rejected")
        self.assertIn("missing-halo", halo["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, halo["reasons"])
        self.assertIn("halo:1", halo["preservedResults"])
        stale = evaluate(payload(site="boundary", staleRead=True, discontinuity=True))
        self.assertEqual(stale["decision"], "rejected")
        self.assertEqual(stale["rejectedClaims"], ["stale-read", "discontinuity"])
        self.assertIn("site:boundary", stale["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "site": "center"},
            {**valid, "borderPolicy": "wrap"},
            {**valid, "haloSupport": -1},
            {**valid, "readOutside": "yes"},
            {**valid, "requiredHalo": True},
            {key: value for key, value in valid.items() if key != "site"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
