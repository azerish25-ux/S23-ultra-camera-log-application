"""TC-P060-04 P010 plane geometry fault."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p060_tc04", Path(__file__).resolve().parents[1] / "gates" / "p060_tc04.py"
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
        "nominalWidth": "8",
        "nominalHeight": "4",
        "rowStride": "20",
        "pixelStride": "2",
        "cropLeft": "2",
        "cropTop": "2",
        "cropRight": "6",
        "cropBottom": "4",
        "planeLayout": "420-interleaved",
        "alignment": "msb",
        "plane": "luma",
        "code": "64",
        "guard": "165",
    }
    base.update(overrides)
    return base


class TcP06004(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P060-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.EXPECTED, result["reasons"])
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])

    def test_packet_strings(self):
        self.assertIn("low six-bit-aligned", _MODULE.NEGATIVE)
        self.assertIn("padded rows", _MODULE.REPEAT)

    def test_padded_luma_endpoint_unpacks(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "unpacked")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("code:64", result["preservedResults"])
        self.assertIn("unpacked:64", result["preservedResults"])
        self.assertIn("packed-word:4096", result["preservedResults"])
        self.assertIn("padding-untouched:yes", result["preservedResults"])
        self.assertIn("nominal:8x4", result["preservedResults"])
        self.assertIn("row-padding:4", result["preservedResults"])

    def test_repeat_padded_white_endpoint(self):
        result = evaluate(payload(code="940"))
        self.assertEqual(result["decision"], "unpacked")
        self.assertIn("packed-word:60160", result["preservedResults"])
        self.assertIn("unpacked:940", result["preservedResults"])
        self.assertIn("padding-untouched:yes", result["preservedResults"])

    def test_repeat_chroma_endpoint(self):
        result = evaluate(payload(plane="chroma", pixelStride="4", code="960"))
        self.assertEqual(result["decision"], "unpacked")
        self.assertIn("plane:chroma", result["preservedResults"])
        self.assertIn("unpacked:960", result["preservedResults"])
        self.assertIn("packed-word:61440", result["preservedResults"])
        self.assertIn("code:960", result["preservedResults"])

    def test_low_six_bit_alignment_fails(self):
        result = evaluate(payload(alignment="lsb", code="940"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("low-six-bit-aligned-position", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("packed-word:940", result["preservedResults"])
        self.assertIn("code:940", result["preservedResults"])
        self.assertNotIn("unpacked:940", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "unpacked"})

    def test_repeat_unsupported_plane_layout(self):
        result = evaluate(payload(planeLayout="contiguous-guess"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("unknown-plane-layout", result["rejectedClaims"])
        self.assertIn("written:no", result["preservedResults"])
        self.assertIn("unpacked:not-guessed", result["preservedResults"])
        self.assertIn("nominal:8x4", result["preservedResults"])
        self.assertIn("code:64", result["preservedResults"])

    def test_short_stride_is_a_bounds_failure(self):
        result = evaluate(payload(rowStride="12"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("bounds-violation", result["rejectedClaims"])
        self.assertIn("written:no", result["preservedResults"])
        self.assertIn("nominal:8x4", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {**valid, "code": "1"},
            {**valid, "cropLeft": "0", "cropTop": "0", "cropRight": "8", "cropBottom": "4"},
            {**valid, "plane": "alpha"},
            {**valid, "guard": "256"},
            {k: v for k, v in valid.items() if k != "alignment"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
