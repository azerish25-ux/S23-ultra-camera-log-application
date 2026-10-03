"""TC-P057-04 P010 stride, alignment, and plane layout."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p057_tc04", Path(__file__).resolve().parents[1] / "gates" / "p057_tc04.py"
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
        "layout": "p010-msb",
        "width": 2,
        "height": 1,
        "nominalWidth": 2,
        "nominalHeight": 1,
        "rowStride": 4,
        "code": 512,
    }
    base.update(overrides)
    return base


class TcP05704(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P057-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_msb_row_unpacks_the_code(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "supported_layout")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("unpacked:512", result["preservedResults"])
        self.assertIn("nominal:2x1", result["preservedResults"])
        self.assertIn("code:512", result["preservedResults"])

    def test_low_six_alignment_fails(self):
        result = evaluate(payload(layout="low-six"))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["low-six-alignment"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("unpacked:8", result["preservedResults"])
        self.assertIn("code:512", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "supported_layout"})

    def test_repeat_padded_rows_keep_the_nominal_size(self):
        result = evaluate(payload(layout="padded", rowStride=8))
        self.assertEqual(result["decision"], "supported_layout")
        self.assertIn("unpacked:512", result["preservedResults"])
        self.assertIn("stride:8", result["preservedResults"])
        self.assertIn("nominal:2x1", result["preservedResults"])

    def test_repeat_chroma_endpoint_and_unsupported_planes(self):
        for layout in ("chroma-endpoint", "unsupported-planes"):
            result = evaluate(payload(layout=layout))
            self.assertEqual(result["decision"], "rejected")
            self.assertEqual(result["rejectedClaims"], [layout])
            self.assertIn("nominal:2x1", result["preservedResults"])
            self.assertIn(f"layout:{layout}", result["preservedResults"])

    def test_changed_geometry_keeps_nominal_dimensions(self):
        result = evaluate(payload(width=2, height=1, nominalWidth=4, nominalHeight=2, rowStride=4))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["geometry-changed"])
        self.assertIn("nominal:4x2", result["preservedResults"])
        self.assertIn("geometry:2x1", result["preservedResults"])

    def test_short_stride_fails_bounds(self):
        result = evaluate(payload(width=4, nominalWidth=4, rowStride=4))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["stride-bounds"])
        self.assertIn("nominal:4x1", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {**valid, "code": 1024},
            {**valid, "rowStride": 3},
            {**valid, "layout": "nv12"},
            {**valid, "width": True},
            {**valid, "layout": "padded", "rowStride": 4},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
