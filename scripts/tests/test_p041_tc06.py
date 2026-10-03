"""TC-P041-06 shading coordinate mismatch."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p041_tc06", Path(__file__).resolve().parents[1] / "gates" / "p041_tc06.py"
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
        "sourceCrop": "4000x3000+0+0",
        "mapCrop": "4000x3000+0+0",
        "sourceCfa": "RGGB",
        "mapCfa": "RGGB",
        "orientation": "source",
        "conversion": "none",
        "sourceWidth": 4000,
        "sourceHeight": 3000,
        "mapWidth": 4000,
        "mapHeight": 3000,
    }
    base.update(overrides)
    return base


class TcP04106(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P041-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_display_coordinates_without_source_mapping_fail(self):
        result = evaluate(payload(orientation="display"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("display-coordinates-without-source-map", result["rejectedClaims"])
        self.assertIn("sourceCrop:4000x3000+0+0", result["preservedResults"])
        self.assertIn("mapCrop:4000x3000+0+0", result["preservedResults"])
        self.assertIn("orientation:display", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_odd_crop_origin_repeat_is_detected(self):
        result = evaluate(payload(mapCrop="4000x3000+1+0"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("odd-crop-origin", result["rejectedClaims"])
        self.assertIn("crop-mismatch", result["rejectedClaims"])
        self.assertIn("mapCrop:4000x3000+1+0", result["preservedResults"])
        self.assertIn("sourceCrop:4000x3000+0+0", result["preservedResults"])

    def test_rotated_output_repeat_is_detected(self):
        result = evaluate(payload(orientation="rotated"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("rotated-output", result["rejectedClaims"])
        self.assertIn("orientation:rotated", result["preservedResults"])
        self.assertIn("source:4000x3000", result["preservedResults"])

    def test_changed_source_dimensions_repeat_is_detected(self):
        result = evaluate(payload(sourceWidth=4080, sourceHeight=3072, mapWidth=4000, mapHeight=3000))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("dimension-change", result["rejectedClaims"])
        self.assertIn("source:4080x3072", result["preservedResults"])
        self.assertIn("map:4000x3000", result["preservedResults"])

    def test_verified_conversion_keeps_both_crops(self):
        result = evaluate(payload(mapCrop="4000x3000+1+2", conversion="verified", sourceCfa="RGGB", mapCfa="GRBG"))
        self.assertEqual(result["decision"], "coordinate_converted")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("mapCrop:4000x3000+1+2", result["preservedResults"])
        self.assertIn("sourceCfa:RGGB", result["preservedResults"])
        self.assertIn("mapCfa:GRBG", result["preservedResults"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_cfa_origin_mismatch_without_conversion_fails(self):
        result = evaluate(payload(mapCfa="BGGR"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("cfa-origin-mismatch", result["rejectedClaims"])
        self.assertIn("mapCfa:BGGR", result["preservedResults"])

    def test_matched_coordinates_are_not_a_shading_certificate(self):
        result = evaluate(payload())
        self.assertEqual(result["decision"], "coordinates_matched")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("matched coordinates are not a measured shading certificate", result["openQuestions"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "sourceCrop": "4000x3000+0"},
            {**valid, "orientation": "mirror"},
            {**valid, "conversion": "guessed"},
            {**valid, "sourceCfa": "RGBG"},
            {**valid, "sourceWidth": True},
            {**valid, "mapHeight": 0},
            {**valid, "mapWidth": 9000},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
