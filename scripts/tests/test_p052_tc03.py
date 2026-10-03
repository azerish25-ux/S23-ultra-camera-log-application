"""TC-P052-03 boundary and halo support."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p052_tc03", Path(__file__).resolve().parents[1] / "gates" / "p052_tc03.py"
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
        "borderPolicy": "omit-missing",
        "impulse": "12",
        "readOutsideRows": False,
        "haloIgnored": False,
        "staleRead": False,
        "discontinuity": False,
    }
    base.update(overrides)
    return base


class TcP05203(unittest.TestCase):
    def test_corner_holds_omit_missing_border(self):
        result = evaluate(payload())
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P052-03")
        self.assertEqual(result["decision"], "border-held")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("impulse:12", result["preservedResults"])
        self.assertIn("policy:omit-missing", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_negative_outside_rows_keeps_impulse(self):
        result = evaluate(payload(site="row-buffer", readOutsideRows=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("outside-rows", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("impulse:12", result["preservedResults"])
        self.assertIn("site:row-buffer", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "border-held"})

    def test_ignored_halo_fails(self):
        result = evaluate(payload(site="tile-seam", haloIgnored=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("ignored-halo", result["rejectedClaims"])
        self.assertIn("impulse:12", result["preservedResults"])

    def test_repeat_corner_tl(self):
        result = evaluate(payload(site="corner-tl"))
        self.assertEqual(result["decision"], "border-held")
        self.assertIn("site:corner-tl", result["preservedResults"])

    def test_repeat_corner_br(self):
        result = evaluate(payload(site="corner-br"))
        self.assertEqual(result["decision"], "border-held")
        self.assertIn("site:corner-br", result["preservedResults"])
        self.assertIn("impulse:12", result["preservedResults"])

    def test_repeat_kernel_boundaries(self):
        for site in ("kernel-left", "kernel-right", "kernel-top", "kernel-bottom"):
            with self.subTest(site=site):
                result = evaluate(payload(site=site))
                self.assertEqual(result["decision"], "border-held")
                self.assertIn(f"site:{site}", result["preservedResults"])

    def test_stale_read_preserves_impulse(self):
        result = evaluate(payload(site="corner-tr", staleRead=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("stale-read", result["rejectedClaims"])
        self.assertIn("impulse:12", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "site"},
            {**valid, "extra": True},
            {**valid, "site": "middle"},
            {**valid, "borderPolicy": "replicate"},
            {**valid, "readOutsideRows": "false"},
            {**valid, "impulse": "12.0"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
