"""TC-P054-03 boundary and halo support."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p054_tc03", Path(__file__).resolve().parents[1] / "gates" / "p054_tc03.py"
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
        "site": "interior",
        "feature": "edge",
        "borderPolicy": "replicate",
        "halo": "2",
        "retainedRows": "8",
        "readOutside": False,
        "haloIgnored": False,
        "staleRead": False,
    }
    base.update(overrides)
    return base


class TcP05403(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P054-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])
        self.assertIn(result["preservedResults"][0], result["preservedResults"])

    def test_repeat_four_corners_hold_the_border_policy(self):
        for site in ("corner-tl", "corner-tr", "corner-bl", "corner-br"):
            result = evaluate(payload(site=site, feature="impulse", borderPolicy="mirror"))
            self.assertContract(result)
            self.assertEqual(result["decision"], "border-held")
            self.assertEqual(result["rejectedClaims"], [])
            self.assertIn(site, result["preservedResults"])
            self.assertIn("mirror", result["preservedResults"])
            self.assertIn("halo:2", result["preservedResults"])

    def test_repeat_kernel_support_boundaries(self):
        for site in ("kernel-left", "kernel-right", "kernel-top", "kernel-bottom"):
            result = evaluate(payload(site=site, halo="1", retainedRows="1", feature="edge"))
            self.assertEqual(result["decision"], "border-held")
            self.assertIn(site, result["preservedResults"])
            self.assertIn("halo:1", result["preservedResults"])
            self.assertIn("rows:1", result["preservedResults"])

    def test_row_buffer_and_tile_seam_use_the_declared_policy(self):
        for site in ("row-buffer", "tile-seam"):
            result = evaluate(payload(site=site, borderPolicy="constant-zero"))
            self.assertEqual(result["decision"], "border-held")
            self.assertIn(site, result["preservedResults"])
            self.assertIn("constant-zero", result["preservedResults"])

    def test_negative_read_outside_retained_rows_fails(self):
        result = evaluate(payload(site="row-buffer", readOutside=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("outside-retained-rows", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("row-buffer", result["preservedResults"])
        self.assertIn("rows:8", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "border-held"})

    def test_ignored_halo_and_short_rows_fail(self):
        ignored = evaluate(payload(site="kernel-left", haloIgnored=True))
        self.assertEqual(ignored["decision"], "rejected")
        self.assertIn("halo-ignored", ignored["rejectedClaims"])
        self.assertIn("kernel-left", ignored["preservedResults"])
        short = evaluate(payload(site="corner-br", halo="2", retainedRows="1"))
        self.assertEqual(short["decision"], "rejected")
        self.assertIn("missing-halo-support", short["rejectedClaims"])
        self.assertIn("corner-br", short["preservedResults"])
        stale = evaluate(payload(site="tile-seam", staleRead=True, readOutside=True))
        self.assertEqual(stale["rejectedClaims"], ["outside-retained-rows", "stale-read"])
        self.assertIn("tile-seam", stale["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "site"},
            {**valid, "extra": True},
            {**valid, "site": "corner"},
            {**valid, "feature": "dot"},
            {**valid, "borderPolicy": "wrap"},
            {**valid, "halo": "0"},
            {**valid, "retainedRows": "08"},
            {**valid, "readOutside": "true"},
            {**valid, "haloIgnored": 0},
            {**valid, "staleRead": None},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
