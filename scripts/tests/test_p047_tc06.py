"""TC-P047-06 shading maps do not jump into display coordinates."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p047_tc06", Path(__file__).resolve().parents[1] / "gates" / "p047_tc06.py"
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
        "sourceCrop": "4000x3000+8+8",
        "mapCrop": "4000x3000+8+8",
        "sourceOrientation": 0,
        "mapOrientation": 0,
        "sourceCfa": "RGGB",
        "mapCfa": "RGGB",
        "sourceWidth": 4000,
        "sourceHeight": 3000,
        "mapWidth": 4000,
        "mapHeight": 3000,
        "displayWithoutMapping": False,
        "verifiedConversion": False,
    }
    base.update(overrides)
    return base


class TcP04706(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P047-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn("map:shade-a", result["preservedResults"])

    def test_constants(self):
        self.assertIn("CFA origin", _MODULE.INTERVENTION)
        self.assertIn("coordinate conversion", _MODULE.EXPECTED)
        self.assertIn("display coordinates", _MODULE.NEGATIVE)

    def test_matching_coordinates_are_mapped(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "mapped")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("sourceCrop:4000x3000+8+8", result["preservedResults"])
        self.assertIn("sourceSize:4000x3000", result["preservedResults"])

    def test_odd_crop_origin_is_rejected(self):
        result = evaluate(payload(sourceCrop="4000x3000+1+0", mapCrop="4000x3000+1+0"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["coordinate-mismatch"])
        self.assertIn("sourceCrop:4000x3000+1+0", result["preservedResults"])
        self.assertIn("odd crop origin detected", result["reasons"])

    def test_rotated_output_repeat(self):
        result = evaluate(payload(mapOrientation=90))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["coordinate-mismatch"])
        self.assertIn("mapOrientation:90", result["preservedResults"])
        self.assertIn("sourceOrientation:0", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "mapped"})

    def test_changed_source_dimensions_repeat(self):
        result = evaluate(payload(sourceWidth=3840, sourceHeight=2160))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("coordinate-mismatch", result["rejectedClaims"])
        self.assertIn("sourceSize:3840x2160", result["preservedResults"])
        self.assertIn("mapSize:4000x3000", result["preservedResults"])

    def test_display_coordinates_without_mapping_fail(self):
        result = evaluate(payload(displayWithoutMapping=True, verifiedConversion=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["display-coordinates-without-mapping"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("sourceCrop:4000x3000+8+8", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "mapped", "converted"})

    def test_verified_conversion_of_a_rotated_map(self):
        result = evaluate(payload(mapOrientation=180, verifiedConversion=True))
        self.assertEqual(result["decision"], "converted")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("mapOrientation:180", result["preservedResults"])
        self.assertIn("separately verified coordinate conversion", " ".join(result["reasons"]))
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "sourceCrop": "4000x3000+8"},
            {**valid, "sourceOrientation": 45},
            {**valid, "sourceCfa": "RGBG"},
            {**valid, "sourceWidth": True},
            {**valid, "displayWithoutMapping": "false"},
            {k: v for k, v in valid.items() if k != "mapId"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
