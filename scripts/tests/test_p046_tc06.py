"""TC-P046-06 shading coordinate mismatch."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p046_tc06", Path(__file__).resolve().parents[1] / "gates" / "p046_tc06.py"
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
        "mapId": "shade-0",
        "correctionSpace": "source",
        "cropX": 0,
        "cropY": 0,
        "orientation": "native",
        "sourceWidth": 100,
        "sourceHeight": 80,
        "mapWidth": 100,
        "mapHeight": 80,
        "verifiedConversion": False,
    }
    base.update(overrides)
    return base


class TcP04606(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P046-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_source_alignment_is_not_a_certificate(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "source_aligned")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("crop:0,0", result["preservedResults"])
        self.assertIn("source:100x80", result["preservedResults"])
        self.assertIn("coordinate conversion", _MODULE.EXPECTED)

    def test_odd_crop_origin_repeat(self):
        result = evaluate(payload(cropX=1, cropY=2))
        self.assertEqual(result["decision"], "mismatch")
        self.assertEqual(result["rejectedClaims"], ["odd-crop-origin"])
        self.assertIn("crop:1,2", result["preservedResults"])
        self.assertIn("map:shade-0", result["preservedResults"])

    def test_rotated_output_repeat(self):
        result = evaluate(payload(orientation="rotated-90"))
        self.assertEqual(result["decision"], "mismatch")
        self.assertEqual(result["rejectedClaims"], ["rotated-output"])
        self.assertIn("orientation:rotated-90", result["preservedResults"])
        self.assertIn("source:100x80", result["preservedResults"])

    def test_changed_source_dimensions_repeat(self):
        result = evaluate(payload(sourceWidth=101, sourceHeight=80))
        self.assertEqual(result["decision"], "mismatch")
        self.assertEqual(result["rejectedClaims"], ["source-dimension-mismatch"])
        self.assertIn("source:101x80", result["preservedResults"])
        self.assertIn("map-size:100x80", result["preservedResults"])

    def test_display_coordinates_without_mapping_fail(self):
        result = evaluate(payload(correctionSpace="display", cropX=1, cropY=0))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "converted", "mismatch"})
        self.assertEqual(
            result["rejectedClaims"],
            ["display-without-source-mapping", "odd-crop-origin"],
        )
        self.assertIn("space:display", result["preservedResults"])
        self.assertIn("crop:1,0", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_verified_conversion_keeps_the_original_crop(self):
        result = evaluate(payload(correctionSpace="display", orientation="rotated-180", verifiedConversion=True))
        self.assertEqual(result["decision"], "converted")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("orientation:rotated-180", result["preservedResults"])
        self.assertIn("space:display", result["preservedResults"])
        self.assertIn("verified-conversion:true", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "orientation"},
            {**valid, "extra": True},
            {**valid, "correctionSpace": "preview"},
            {**valid, "cropX": True},
            {**valid, "orientation": "rotated"},
            {**valid, "sourceWidth": 0},
            {**valid, "verifiedConversion": "yes"},
            {**valid, "mapId": ""},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
