"""TC-P064-04 P010 plane geometry fault."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p064_tc04", Path(__file__).resolve().parents[1] / "gates" / "p064_tc04.py"
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
        "width": 1920,
        "height": 1080,
        "stride": 1920,
        "crop": "none",
        "layout": "p010-msb",
        "boundsChecked": True,
        "unpackedMatches": True,
        "explicitlySupported": True,
    }
    base.update(overrides)
    return base


class TcP06404(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P064-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_packet_strings(self):
        self.assertEqual(
            _MODULE.NEGATIVE,
            "Writing ten-bit values into the low six-bit-aligned position must fail.",
        )
        self.assertIn("padded rows", _MODULE.REPEAT)
        self.assertIn("unsupported plane", _MODULE.REPEAT)

    def test_supported_msb_layout_is_withheld(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("1920x1080", result["preservedResults"])
        self.assertIn("layout:p010-msb", result["preservedResults"])

    def test_low_six_alignment_fails_and_keeps_dimensions(self):
        result = evaluate(payload(layout="low-six", explicitlySupported=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["low-six-bit-aligned"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("1920x1080", result["preservedResults"])
        self.assertIn("stride:1920", result["preservedResults"])
        self.assertIn("layout:low-six", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "withheld"})

    def test_repeat_padded_rows(self):
        result = evaluate(payload(layout="padded-row", stride=2048))
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("1920x1080", result["preservedResults"])
        self.assertIn("stride:2048", result["preservedResults"])
        self.assertIn("layout:padded-row", result["preservedResults"])
        short = evaluate(payload(layout="padded-row", stride=1920))
        self.assertEqual(short["decision"], "rejected")
        self.assertIn("padding-not-in-stride", short["rejectedClaims"])
        self.assertIn("1920x1080", short["preservedResults"])

    def test_repeat_chroma_endpoint(self):
        result = evaluate(payload(layout="chroma-endpoint", stride=1920))
        self.assertEqual(result["decision"], "withheld")
        self.assertIn("layout:chroma-endpoint", result["preservedResults"])
        self.assertIn("1920x1080", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_repeat_unsupported_plane(self):
        result = evaluate(payload(layout="unsupported", explicitlySupported=False))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("unsupported-plane", result["rejectedClaims"])
        self.assertIn("1920x1080", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "withheld"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "width": 0},
            {**valid, "width": True},
            {**valid, "layout": "nv12"},
            {**valid, "boundsChecked": 1},
            {**valid, "crop": "padded"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
