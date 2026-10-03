"""TC-P052-02 CFA and crop parity."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p052_tc02", Path(__file__).resolve().parents[1] / "gates" / "p052_tc02.py"
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
        "cfa": "RGGB",
        "cropLeft": 0,
        "cropTop": 0,
        "x": 0,
        "y": 0,
        "site": "interior",
        "parityReset": False,
        "observed": "R",
        "red": "0.2",
        "green": "0.5",
        "blue": "0.9",
    }
    base.update(overrides)
    return base


class TcP05202(unittest.TestCase):
    def test_even_origin_keeps_rggb_red(self):
        result = evaluate(payload())
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P052-02")
        self.assertEqual(result["decision"], "aligned")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("expected:R", result["preservedResults"])
        self.assertIn("samples:0.2,0.5,0.9", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_negative_parity_reset_keeps_expected_channel(self):
        result = evaluate(payload(cropLeft=1, cropTop=0, observed="R", parityReset=True, site="border"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("parity-reset", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("expected:G", result["preservedResults"])
        self.assertIn("reset-channel:R", result["preservedResults"])
        self.assertIn("samples:0.2,0.5,0.9", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "aligned"})

    def test_odd_origin_without_reset_is_green(self):
        result = evaluate(payload(cropLeft=1, observed="G", site="border"))
        self.assertEqual(result["decision"], "aligned")
        self.assertIn("crop:1,0", result["preservedResults"])
        self.assertIn("expected:G", result["preservedResults"])

    def test_repeat_border(self):
        result = evaluate(payload(x=0, y=1, observed="G", site="border"))
        self.assertEqual(result["decision"], "aligned")
        self.assertIn("site:border", result["preservedResults"])
        self.assertIn("expected:G", result["preservedResults"])

    def test_repeat_padded_row(self):
        result = evaluate(payload(cfa="BGGR", x=0, y=0, observed="B", site="padded-row"))
        self.assertEqual(result["decision"], "aligned")
        self.assertIn("cfa:BGGR", result["preservedResults"])
        self.assertIn("site:padded-row", result["preservedResults"])

    def test_repeat_rotated(self):
        result = evaluate(payload(cfa="GRBG", x=1, y=0, observed="R", site="rotated"))
        self.assertEqual(result["decision"], "aligned")
        self.assertIn("site:rotated", result["preservedResults"])
        self.assertIn("expected:R", result["preservedResults"])

    def test_channel_mismatch_preserves_samples(self):
        result = evaluate(payload(observed="B"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("channel-mismatch", result["rejectedClaims"])
        self.assertIn("expected:R", result["preservedResults"])
        self.assertIn("observed:B", result["preservedResults"])

    def test_every_cfa_at_origin(self):
        expected = {"RGGB": "R", "BGGR": "B", "GRBG": "G", "GBRG": "G"}
        for cfa, channel in expected.items():
            with self.subTest(cfa=cfa):
                result = evaluate(payload(cfa=cfa, observed=channel))
                self.assertEqual(result["decision"], "aligned")
                self.assertIn(f"expected:{channel}", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "cfa"},
            {**valid, "extra": 1},
            {**valid, "cfa": "RGB"},
            {**valid, "parityReset": "false"},
            {**valid, "red": "0.20"},
            {**valid, "green": "0.2"},
            {**valid, "site": "seam"},
            {**valid, "cropLeft": -1},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
