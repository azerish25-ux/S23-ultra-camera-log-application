"""TC-P042-06 shading coordinate mismatch."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p042_tc06", Path(__file__).resolve().parents[1] / "gates" / "p042_tc06.py"
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
        "shadeId": "shade-a",
        "sourceWidth": 4032,
        "sourceHeight": 3024,
        "appliedWidth": 4032,
        "appliedHeight": 3024,
        "cropX": 0,
        "cropY": 0,
        "orientation": "identity",
        "mapping": "none",
    }
    base.update(overrides)
    return base


class TcP04206(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P042-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn("crop", _MODULE.INTERVENTION)
        self.assertIn("verified", _MODULE.EXPECTED)
        self.assertEqual(
            _MODULE.NEGATIVE,
            "Applying shading in display coordinates without source mapping must fail.",
        )

    def test_display_coordinates_are_rejected(self):
        result = evaluate(payload(mapping="display"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["display-coordinates"])
        self.assertIn("source:4032x3024", result["preservedResults"])
        self.assertIn("shade:shade-a", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_repeat_odd_crop_origin_is_a_mismatch(self):
        result = evaluate(payload(cropX=1, cropY=2))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "converted"})
        self.assertEqual(result["rejectedClaims"], ["coordinate-mismatch"])
        self.assertIn("crop:1,2", result["preservedResults"])
        self.assertIn("source:4032x3024", result["preservedResults"])

    def test_repeat_rotated_output_is_a_mismatch(self):
        result = evaluate(payload(orientation="rotated"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("orientation:rotated", result["preservedResults"])
        self.assertIn("coordinate-mismatch", result["rejectedClaims"])
        self.assertIn("applied:4032x3024", result["preservedResults"])

    def test_repeat_changed_source_dimensions(self):
        result = evaluate(payload(appliedWidth=1920, appliedHeight=1080))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("source:4032x3024", result["preservedResults"])
        self.assertIn("applied:1920x1080", result["preservedResults"])
        self.assertIn("coordinate-mismatch", result["rejectedClaims"])

    def test_verified_conversion_is_not_a_measurement(self):
        result = evaluate(payload(mapping="verified", cropX=1, orientation="rotated"))
        self.assertEqual(result["decision"], "converted")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("crop:1,0", result["preservedResults"])
        self.assertIn(
            "verified conversion is not a physical shading measurement",
            result["openQuestions"],
        )

    def test_matching_source_is_withheld(self):
        result = evaluate(payload())
        self.assertEqual(result["decision"], "withheld")
        self.assertIn("source:4032x3024", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "sourceWidth": True},
            {**valid, "cropX": -1},
            {**valid, "mapping": "display_space"},
            {**valid, "orientation": "flipped"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
