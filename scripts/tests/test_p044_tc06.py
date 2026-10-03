"""TC-P044-06 shading coordinate mismatch."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p044_tc06", Path(__file__).resolve().parents[1] / "gates" / "p044_tc06.py"
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
        "sourceWidth": 3840,
        "sourceHeight": 2160,
        "mapWidth": 3840,
        "mapHeight": 2160,
    }
    base.update(overrides)
    return base


class TcP04406(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P044-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_constants_encode_intervention_expected_and_negative(self):
        self.assertIn("crop, orientation, or CFA origin", _MODULE.INTERVENTION)
        self.assertIn("verified coordinate conversion", _MODULE.EXPECTED)
        self.assertIn("display coordinates", _MODULE.NEGATIVE)

    def test_matching_coordinates_are_aligned(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "aligned")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("source-crop:0,0", result["preservedResults"])
        self.assertIn("source-size:3840x2160", result["preservedResults"])
        self.assertIn("map-size:3840x2160", result["preservedResults"])

    def test_odd_crop_origin_repeat_is_a_mismatch(self):
        result = evaluate(payload(appliedCrop="1,1"))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["coordinate-mismatch"])
        self.assertIn("source-crop:0,0", result["preservedResults"])
        self.assertIn("applied-crop:1,1", result["preservedResults"])
        self.assertIn("cfa:0,0", result["preservedResults"])

    def test_rotated_output_repeat_is_detected(self):
        result = evaluate(payload(orientation="rotated"))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "converted"})
        self.assertEqual(result["rejectedClaims"], ["coordinate-mismatch"])
        self.assertIn("orientation:rotated", result["preservedResults"])
        self.assertIn("source-size:3840x2160", result["preservedResults"])

    def test_changed_source_dimensions_repeat_keeps_both_sizes(self):
        result = evaluate(payload(mapWidth=1920, mapHeight=1080))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["coordinate-mismatch"])
        self.assertIn("source-size:3840x2160", result["preservedResults"])
        self.assertIn("map-size:1920x1080", result["preservedResults"])

    def test_verified_conversion_transforms_an_odd_crop(self):
        result = evaluate(payload(appliedCrop="1,1", verifiedConversion=True))
        self.assertEqual(result["decision"], "converted")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("applied-crop:1,1", result["preservedResults"])
        self.assertIn("source-crop:0,0", result["preservedResults"])
        self.assertIn("coordinate conversion was separately verified", result["openQuestions"])

    def test_negative_display_coordinates_without_mapping_cannot_qualify(self):
        result = evaluate(payload(displayCoordinates=True, verifiedConversion=False))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "aligned"})
        self.assertEqual(result["rejectedClaims"], ["display-coordinates-unmapped"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("source-crop:0,0", result["preservedResults"])
        self.assertIn("display:true", result["preservedResults"])
        self.assertIn("source-size:3840x2160", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "sourceCrop"},
            {**valid, "extra": True},
            {**valid, "sourceCrop": "0,0,1"},
            {**valid, "appliedCrop": "01,0"},
            {**valid, "orientation": "flipped"},
            {**valid, "cfaOrigin": "0"},
            {**valid, "displayCoordinates": "false"},
            {**valid, "sourceWidth": 0},
            {**valid, "mapHeight": True},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
