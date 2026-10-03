"""TC-P063-04 P010 plane geometry fault."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p063_tc04", Path(__file__).resolve().parents[1] / "gates" / "p063_tc04.py"
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
        "frameId": "p010-frame",
        "width": 4,
        "height": 2,
        "rowStride": 8,
        "crop": "none",
        "planeLayout": "semi-planar",
        "alignment": "lsb",
        "unpackedCode": "940",
        "expectedCode": "940",
        "boundsOk": True,
    }
    base.update(overrides)
    return base


class TcP06304(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P063-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_packet_strings(self):
        self.assertEqual(
            _MODULE.NEGATIVE,
            "Writing ten-bit values into the low six-bit-aligned position must fail.",
        )
        self.assertIn("nominal dimensions", _MODULE.INTERVENTION)

    def test_low_six_bit_alignment_fails(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("low-six-bit-alignment", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("nominal:4x2", result["preservedResults"])
        self.assertIn("unpacked:940", result["preservedResults"])
        self.assertIn("p010-frame", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "layout_checked"})

    def test_repeat_padded_rows(self):
        result = evaluate(payload(alignment="msb", rowStride=16))
        self.assertEqual(result["decision"], "layout_checked")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("row-stride:16", result["preservedResults"])
        self.assertIn("nominal:4x2", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_repeat_chroma_endpoint_bounds(self):
        result = evaluate(payload(alignment="msb", crop="chroma-endpoint", boundsOk=False))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("bounds-failed", result["rejectedClaims"])
        self.assertIn("crop:chroma-endpoint", result["preservedResults"])
        self.assertIn("nominal:4x2", result["preservedResults"])

    def test_repeat_unsupported_plane_layout(self):
        result = evaluate(payload(alignment="msb", planeLayout="planar"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("unsupported-plane", result["rejectedClaims"])
        self.assertIn("layout:planar", result["preservedResults"])
        self.assertIn("nominal:4x2", result["preservedResults"])

    def test_unpacked_code_mismatch_keeps_both_codes(self):
        result = evaluate(payload(alignment="msb", unpackedCode="100", expectedCode="200"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("unpacked-code-mismatch", result["rejectedClaims"])
        self.assertIn("unpacked:100", result["preservedResults"])
        self.assertIn("expected:200", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "width": True},
            {**valid, "width": 0},
            {**valid, "alignment": "middle"},
            {**valid, "unpackedCode": "1024"},
            {**valid, "boundsOk": "true"},
            {**valid, "planeLayout": "nv12"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
