"""TC-P045-06 shading coordinate mismatch."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p045_tc06", Path(__file__).resolve().parents[1] / "gates" / "p045_tc06.py"
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
_CROP = "4000x3000+0+0"


def payload(**overrides):
    base = {
        "mapId": "shade-1",
        "sourceCrop": _CROP,
        "appliedCrop": _CROP,
        "sourceDimensions": "4000x3000",
        "appliedDimensions": "4000x3000",
        "orientation": "sensor",
        "cfaOrigin": "matched",
        "verifiedConversion": False,
        "displayUnmapped": False,
    }
    base.update(overrides)
    return base


class TcP04506(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P045-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn("map:shade-1", result["preservedResults"])

    def test_matched_coordinates_stay_mapped(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "mapped")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn(f"source-crop:{_CROP}", result["preservedResults"])
        self.assertIn(f"applied-crop:{_CROP}", result["preservedResults"])

    def test_negative_display_coordinates_without_source_mapping_fail(self):
        result = evaluate(payload(displayUnmapped=True, orientation="display"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("display-coordinates-unmapped", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn(f"source-crop:{_CROP}", result["preservedResults"])
        self.assertIn("source-dimensions:4000x3000", result["preservedResults"])

    def test_verified_conversion_does_not_launder_display_shading(self):
        result = evaluate(payload(displayUnmapped=True, verifiedConversion=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("display-coordinates-unmapped", result["rejectedClaims"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "converted"})

    def test_repeat_odd_crop_origin_without_conversion(self):
        odd = "4000x3000+1+0"
        result = evaluate(payload(appliedCrop=odd, cfaOrigin="odd"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("crop-mismatch", result["rejectedClaims"])
        self.assertIn("cfa-origin-mismatch", result["rejectedClaims"])
        self.assertIn(f"applied-crop:{odd}", result["preservedResults"])
        self.assertIn(f"source-crop:{_CROP}", result["preservedResults"])

    def test_repeat_rotated_output_with_verified_conversion(self):
        result = evaluate(payload(orientation="rotated", verifiedConversion=True))
        self.assertEqual(result["decision"], "converted")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("orientation:rotated", result["preservedResults"])
        self.assertTrue(any("verified coordinate conversion" in item for item in result["reasons"]))

    def test_repeat_changed_source_dimensions(self):
        result = evaluate(payload(appliedDimensions="1920x1080"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("dimension-mismatch", result["rejectedClaims"])
        self.assertIn("source-dimensions:4000x3000", result["preservedResults"])
        self.assertIn("applied-dimensions:1920x1080", result["preservedResults"])

    def test_shifted_cfa_without_conversion_is_rejected(self):
        result = evaluate(payload(cfaOrigin="shifted"))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["cfa-origin-mismatch"])
        self.assertIn("cfa:shifted", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "mapId"},
            {**valid, "extra": True},
            {**valid, "sourceCrop": "4000x3000"},
            {**valid, "orientation": "mirrored"},
            {**valid, "verifiedConversion": "true"},
            {**valid, "displayUnmapped": 0},
            {**valid, "sourceDimensions": "4000X3000"},
            {**valid, "cfaOrigin": "RGGB"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
