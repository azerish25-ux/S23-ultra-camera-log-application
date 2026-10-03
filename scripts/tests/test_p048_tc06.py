"""TC-P048-06 display shading without source mapping fails."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p048_tc06", Path(__file__).resolve().parents[1] / "gates" / "p048_tc06.py"
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
        "sourceCrop": "0,0",
        "appliedCrop": "0,0",
        "orientation": "native",
        "cfaOrigin": "0,0",
        "displayCoordinates": False,
        "verifiedConversion": False,
        "sourceWidth": 4000,
        "sourceHeight": 3000,
        "mapWidth": 4000,
        "mapHeight": 3000,
    }
    base.update(overrides)
    return base


class TcP04806(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P048-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn("source-size:4000x3000", result["preservedResults"])

    def test_constants(self):
        self.assertIn("crop, orientation, or CFA origin", _MODULE.INTERVENTION)
        self.assertIn("coordinate conversion", _MODULE.EXPECTED)
        self.assertIn("display coordinates", _MODULE.NEGATIVE)

    def test_aligned_map_is_not_qualified(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "aligned")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("source-crop:0,0", result["preservedResults"])

    def test_negative_display_coordinates_without_mapping(self):
        result = evaluate(payload(displayCoordinates=True, verifiedConversion=False))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("display-coordinates-unmapped", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("map-size:4000x3000", result["preservedResults"])

    def test_repeat_odd_crop_origin(self):
        result = evaluate(payload(sourceCrop="1,0", appliedCrop="0,0"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("coordinate-mismatch", result["rejectedClaims"])
        self.assertIn("source-crop:1,0", result["preservedResults"])
        self.assertIn("applied-crop:0,0", result["preservedResults"])

    def test_repeat_rotated_output_and_changed_dimensions(self):
        rotated = evaluate(payload(orientation="rotated"))
        resized = evaluate(payload(mapWidth=1920, mapHeight=1080))
        self.assertEqual(rotated["decision"], "rejected")
        self.assertIn("orientation:rotated", rotated["preservedResults"])
        self.assertEqual(resized["decision"], "rejected")
        self.assertIn("map-size:1920x1080", resized["preservedResults"])
        self.assertIn("source-size:4000x3000", resized["preservedResults"])
        self.assertNotIn(rotated["decision"], {"qualified", "allowed"})

    def test_verified_conversion_keeps_both_crops(self):
        result = evaluate(
            payload(sourceCrop="1,1", appliedCrop="0,0", verifiedConversion=True, displayCoordinates=False)
        )
        self.assertEqual(result["decision"], "converted")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("source-crop:1,1", result["preservedResults"])
        self.assertIn("applied-crop:0,0", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        for item in (None, {}, {**valid, "sourceCrop": "1"}, {**valid, "sourceWidth": 0}):
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
