"""TC-P043-06 shading coordinate mismatch."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p043_tc06", Path(__file__).resolve().parents[1] / "gates" / "p043_tc06.py"
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
        "mapId": "shade-a",
        "sourceCrop": "4000x3000+0+0",
        "mapCrop": "4000x3000+0+0",
        "sourceCfa": "RGGB",
        "mapCfa": "RGGB",
        "orientation": "native",
        "sourceWidth": "4000",
        "sourceHeight": "3000",
        "displayCoordinates": False,
        "verifiedConversion": False,
    }
    base.update(overrides)
    return base


class TcP04306(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P043-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn("map:shade-a", result["preservedResults"])
        self.assertIn("sourceCrop:4000x3000+0+0", result["preservedResults"])

    def test_display_coordinates_without_source_mapping_fail(self):
        result = evaluate(payload(displayCoordinates=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "converted", "coordinates_aligned"})
        self.assertEqual(result["rejectedClaims"], ["display-without-source-mapping"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("mapCrop:4000x3000+0+0", result["preservedResults"])
        self.assertIn("source:4000x3000", result["preservedResults"])

    def test_odd_crop_origin_is_detected(self):
        result = evaluate(
            payload(sourceCrop="3998x2998+1+0", mapCrop="3998x2998+1+0")
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("odd-crop-origin", result["rejectedClaims"])
        self.assertIn("sourceCrop:3998x2998+1+0", result["preservedResults"])
        self.assertIn("mapCrop:3998x2998+1+0", result["preservedResults"])
        self.assertIn("source:4000x3000", result["preservedResults"])

    def test_rotated_output_is_detected(self):
        result = evaluate(payload(orientation="rotated"))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["rotated-output"])
        self.assertIn("orientation:rotated", result["preservedResults"])
        self.assertIn("sourceCrop:4000x3000+0+0", result["preservedResults"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_changed_source_dimensions_are_detected(self):
        result = evaluate(payload(sourceWidth="3840", sourceHeight="2160"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("dimension-mismatch", result["rejectedClaims"])
        self.assertIn("source:3840x2160", result["preservedResults"])
        self.assertIn("sourceCrop:4000x3000+0+0", result["preservedResults"])
        self.assertIn("mapCrop:4000x3000+0+0", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_verified_conversion_keeps_both_crops(self):
        result = evaluate(
            payload(mapCrop="4000x3000+2+0", verifiedConversion=True)
        )
        self.assertEqual(result["decision"], "converted")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("sourceCrop:4000x3000+0+0", result["preservedResults"])
        self.assertIn("mapCrop:4000x3000+2+0", result["preservedResults"])
        self.assertIn("separately verified coordinate conversion", result["reasons"])

    def test_aligned_coordinates_are_not_qualification(self):
        result = evaluate(payload())
        self.assertEqual(result["decision"], "coordinates_aligned")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("map:shade-a", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "sourceCrop": "4000x3000"},
            {**valid, "sourceCfa": "rggb"},
            {**valid, "orientation": "90"},
            {**valid, "displayCoordinates": "false"},
            {**valid, "sourceWidth": "0"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
