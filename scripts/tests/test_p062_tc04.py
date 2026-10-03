"""TC-P062-04 P010 plane geometry fault."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p062_tc04", Path(__file__).resolve().parents[1] / "gates" / "p062_tc04.py"
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
        "sampleId": "p010-row",
        "width": 8,
        "height": 2,
        "rowStride": 16,
        "x": 0,
        "y": 0,
        "plane": "luma",
        "planeLayout": "p010",
        "alignment": "msb",
        "crop": "none",
        "code": 512,
    }
    base.update(overrides)
    return base


class TcP06204(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P062-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_packet_strings(self):
        self.assertEqual(
            _MODULE.NEGATIVE,
            "Writing ten-bit values into the low six-bit-aligned position must fail.",
        )

    def test_supported_msb_layout_unpacks_the_code(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "layout_checked")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("nominal:8x2", result["preservedResults"])
        self.assertIn("code:512", result["preservedResults"])
        self.assertIn("unpacked:512", result["preservedResults"])
        self.assertIn("p010-row", result["preservedResults"])

    def test_low_six_bit_alignment_fails(self):
        result = evaluate(payload(alignment="lsb"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["low-six-bit-alignment"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("nominal:8x2", result["preservedResults"])
        self.assertIn("code:512", result["preservedResults"])
        self.assertIn("unpacked:8", result["preservedResults"])
        self.assertIn("alignment:lsb", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "layout_checked"})

    def test_repeat_padded_rows(self):
        result = evaluate(payload(sampleId="padded", width=4, height=2, rowStride=16, x=3, y=1))
        self.assertEqual(result["decision"], "layout_checked")
        self.assertIn("nominal:4x2", result["preservedResults"])
        self.assertIn("stride:16", result["preservedResults"])
        self.assertIn("unpacked:512", result["preservedResults"])
        self.assertIn("sample:3,1", result["preservedResults"])

    def test_repeat_chroma_endpoint(self):
        result = evaluate(
            payload(
                sampleId="chroma-end",
                width=8,
                height=4,
                rowStride=16,
                x=7,
                y=3,
                plane="chroma",
                code=1000,
            )
        )
        self.assertEqual(result["decision"], "layout_checked")
        self.assertIn("nominal:8x4", result["preservedResults"])
        self.assertIn("plane:chroma", result["preservedResults"])
        self.assertIn("sample:7,3", result["preservedResults"])
        self.assertIn("code:1000", result["preservedResults"])
        self.assertIn("unpacked:1000", result["preservedResults"])

    def test_repeat_unsupported_plane_layout(self):
        result = evaluate(payload(sampleId="planar", planeLayout="i420"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("unsupported-plane-layout", result["rejectedClaims"])
        self.assertIn("nominal:8x2", result["preservedResults"])
        self.assertIn("layout:i420", result["preservedResults"])
        self.assertIn("code:512", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_out_of_bounds_crop_keeps_nominal_dimensions(self):
        result = evaluate(payload(crop="out-of-bounds"))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["bounds"])
        self.assertIn("nominal:8x2", result["preservedResults"])
        self.assertIn("crop:out-of-bounds", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "code"},
            {**valid, "extra": True},
            {**valid, "width": True},
            {**valid, "code": 1024},
            {**valid, "alignment": "middle"},
            {**valid, "planeLayout": "rgb"},
            {**valid, "rowStride": 0},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
