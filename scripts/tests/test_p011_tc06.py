"""TC-P011-06 container dimensions do not certify source geometry."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p011_tc06", Path(__file__).resolve().parents[1] / "gates" / "p011_tc06.py"
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


def rate(numerator=15, denominator=1):
    return {"numerator": numerator, "denominator": denominator}


def payload(**overrides):
    base = {
        "sourceWidth": 4000,
        "sourceHeight": 3000,
        "outputWidth": 3840,
        "outputHeight": 2160,
        "transform": "center_crop",
        "orientationDegrees": 90,
        "containerWidth": 3840,
        "containerHeight": 2160,
        "aeMin": rate(15),
        "aeMax": rate(30),
        "requestedFps": rate(24),
        "containerTimestampsAssigned": False,
    }
    base.update(overrides)
    return base


class TcP01106(unittest.TestCase):
    def assert_contract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P011-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "native_fixed_24"})
        self.assertTrue(result["reasons"])

    def test_encodes_intervention_expected_and_negative(self):
        self.assertIn("crop", _MODULE.INTERVENTION)
        self.assertIn("separately", _MODULE.EXPECTED)
        self.assertIn("Container dimensions", _MODULE.NEGATIVE)

    def test_center_crop_preserves_both_sizes(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "transformed")
        self.assertEqual(
            result["preservedResults"][:2],
            ["source:4000x3000", "output:3840x2160"],
        )
        self.assertIn("ae:15/1-30/1", result["preservedResults"])
        self.assertIn("requested:24/1", result["preservedResults"])
        self.assertEqual(result["rejectedClaims"], ["container-as-source"])
        self.assertIn("orientation metadata is not a source-size change", result["openQuestions"])
        self.assertTrue(any("center_crop" in item for item in result["reasons"]))
        self.assertFalse(any("native" in item for item in result["reasons"]))

    def test_downsample_keeps_source_distinct_from_output(self):
        result = evaluate(
            payload(
                sourceWidth=3840,
                sourceHeight=2160,
                outputWidth=1920,
                outputHeight=1080,
                transform="downsample",
                orientationDegrees=0,
                containerWidth=3840,
                containerHeight=2160,
            )
        )
        self.assertEqual(result["decision"], "transformed")
        self.assertEqual(
            result["preservedResults"][:2],
            ["source:3840x2160", "output:1920x1080"],
        )
        self.assertIn("ae:15/1-30/1", result["preservedResults"])
        self.assertEqual(result["openQuestions"], [])
        self.assertTrue(any("downsample" in item for item in result["reasons"]))

    def test_upscale_does_not_certify_source_resolution(self):
        result = evaluate(
            payload(
                sourceWidth=1920,
                sourceHeight=1080,
                outputWidth=3840,
                outputHeight=2160,
                transform="upscale",
                orientationDegrees=180,
                containerWidth=3840,
                containerHeight=2160,
            )
        )
        self.assertEqual(result["decision"], "transformed")
        self.assertIn("source:1920x1080", result["preservedResults"])
        self.assertIn("output:3840x2160", result["preservedResults"])
        self.assertIn("container-as-source", result["rejectedClaims"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_matching_geometry_is_not_a_cadence_claim(self):
        result = evaluate(
            payload(
                sourceWidth=1920,
                sourceHeight=1080,
                outputWidth=1920,
                outputHeight=1080,
                transform="none",
                orientationDegrees=0,
                containerWidth=1920,
                containerHeight=1080,
                containerTimestampsAssigned=True,
            )
        )
        self.assertEqual(result["decision"], "source_matches")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "native_fixed_24"})
        self.assertIn("1920x1080", result["preservedResults"])
        self.assertIn("native-fixed-24", result["rejectedClaims"])
        self.assertNotIn("container-as-source", result["rejectedClaims"])

    def test_container_alone_does_not_certify_a_matching_source(self):
        result = evaluate(
            payload(
                sourceWidth=1920,
                sourceHeight=1080,
                outputWidth=1920,
                outputHeight=1080,
                transform="none",
                orientationDegrees=270,
                containerWidth=3840,
                containerHeight=2160,
            )
        )
        self.assertEqual(result["decision"], "withheld")
        self.assertIn("container-as-source", result["rejectedClaims"])
        self.assertIn("1920x1080", result["preservedResults"])
        self.assertNotIn("source:1920x1080", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {**valid, "transform": "rotate"},
            {**valid, "orientationDegrees": 45},
            {**valid, "transform": "none"},
            {**valid, "outputWidth": 4000, "outputHeight": 3000},
            {**valid, "sourceWidth": True},
            {**valid, "aeMax": {"numerator": 30, "denominator": 2}},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
