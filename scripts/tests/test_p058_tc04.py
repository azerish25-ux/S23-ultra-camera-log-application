"""TC-P058-04 P010 plane geometry fault."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p058_tc04", Path(__file__).resolve().parents[1] / "gates" / "p058_tc04.py"
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
        "nominalWidth": 1920,
        "nominalHeight": 1080,
        "stride": 3840,
        "layout": "nv12-msb10",
        "crop": "none",
        "unpackedExpected": 940,
        "unpackedObserved": 940,
        "boundsOk": True,
    }
    base.update(overrides)
    return base


class TcP05804(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P058-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn("1920x1080", result["preservedResults"])

    def test_supported_layout_is_checked_not_qualified(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "layout_checked")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("expected:940", result["preservedResults"])
        self.assertIn("observed:940", result["preservedResults"])

    def test_negative_low_six_alignment_fails(self):
        result = evaluate(payload(layout="low-six-align"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("low-six-bit-alignment", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("1920x1080", result["preservedResults"])
        self.assertIn("layout:low-six-align", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_repeat_padded_rows_keep_nominal_dimensions(self):
        result = evaluate(payload(layout="padded-rows", stride=4096))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("padded-rows", result["rejectedClaims"])
        self.assertIn("1920x1080", result["preservedResults"])
        self.assertIn("stride:4096", result["preservedResults"])

    def test_repeat_chroma_endpoint_and_unsupported_planes(self):
        chroma = evaluate(payload(layout="chroma-endpoint"))
        self.assertEqual(chroma["decision"], "rejected")
        self.assertIn("chroma-endpoint", chroma["rejectedClaims"])
        self.assertIn("1920x1080", chroma["preservedResults"])
        planes = evaluate(payload(layout="unsupported-planes"))
        self.assertEqual(planes["decision"], "rejected")
        self.assertIn("unsupported-planes", planes["rejectedClaims"])
        self.assertIn("expected:940", planes["preservedResults"])
        self.assertIn("observed:940", planes["preservedResults"])

    def test_code_mismatch_and_bounds_failure_preserve_both_codes(self):
        result = evaluate(payload(unpackedObserved=64, boundsOk=False))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("unpacked-code", result["rejectedClaims"])
        self.assertIn("bounds", result["rejectedClaims"])
        self.assertIn("expected:940", result["preservedResults"])
        self.assertIn("observed:64", result["preservedResults"])
        self.assertIn("1920x1080", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "layout"},
            {**valid, "extra": True},
            {**valid, "nominalWidth": True},
            {**valid, "layout": "i420"},
            {**valid, "unpackedExpected": 1024},
            {**valid, "boundsOk": 1},
            {**valid, "stride": 0},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
