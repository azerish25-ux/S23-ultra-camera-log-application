"""TC-P013-06 container size is not source geometry."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p013_tc06", Path(__file__).resolve().parents[1] / "gates" / "p013_tc06.py"
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
        "sourceWidth": 3840,
        "sourceHeight": 2160,
        "outputWidth": 1920,
        "outputHeight": 1080,
        "transform": "center_crop",
        "orientationDegrees": 0,
        "containerWidth": 1920,
        "containerHeight": 1080,
    }
    base.update(overrides)
    return base


class TcP01306(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P013-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(result["decision"], {"transformed", "native", "withheld"})
        self.assertTrue(result["reasons"])
        self.assertTrue(result["preservedResults"])

    def test_center_crop_keeps_source_and_output_apart(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "transformed")
        self.assertEqual(result["preservedResults"], ["source:3840x2160", "output:1920x1080"])
        self.assertIn("container-as-source", result["rejectedClaims"])
        self.assertTrue(any("transform center_crop" in item for item in result["reasons"]))
        self.assertTrue(any("not native acquisition" in item for item in result["reasons"]))
        self.assertNotEqual(result["decision"], "native")

    def test_linear_downsample_is_transformed(self):
        result = evaluate(payload(transform="downsample", outputWidth=1280, outputHeight=720,
                                  containerWidth=1280, containerHeight=720))
        self.assertContract(result)
        self.assertEqual(result["decision"], "transformed")
        self.assertIn("source:3840x2160", result["preservedResults"])
        self.assertIn("output:1280x720", result["preservedResults"])
        self.assertTrue(any("transform downsample" in item for item in result["reasons"]))

    def test_upscaled_output_is_not_native_acquisition(self):
        result = evaluate(
            payload(
                sourceWidth=1920,
                sourceHeight=1080,
                outputWidth=3840,
                outputHeight=2160,
                transform="upscale",
                containerWidth=3840,
                containerHeight=2160,
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "transformed")
        self.assertEqual(result["preservedResults"], ["source:1920x1080", "output:3840x2160"])
        self.assertIn("container-as-source", result["rejectedClaims"])
        self.assertNotIn(result["decision"], {"native", "qualified", "allowed"})

    def test_orientation_metadata_does_not_make_a_crop_native(self):
        result = evaluate(payload(orientationDegrees=90))
        self.assertContract(result)
        self.assertEqual(result["decision"], "transformed")
        self.assertTrue(any("orientation 90" in item for item in result["reasons"]))
        self.assertIn("source:3840x2160", result["preservedResults"])
        self.assertIn("output:1920x1080", result["preservedResults"])

    def test_container_dimensions_do_not_certify_matching_source(self):
        result = evaluate(
            payload(
                sourceWidth=1920,
                sourceHeight=1080,
                outputWidth=1920,
                outputHeight=1080,
                transform="none",
                containerWidth=3840,
                containerHeight=2160,
            )
        )
        self.assertEqual(result["decision"], "withheld")
        self.assertIn("container-as-source", result["rejectedClaims"])
        self.assertIn("source:1920x1080", result["preservedResults"])
        self.assertNotIn(result["decision"], {"native", "qualified", "allowed"})

    def test_matching_geometry_is_native_not_qualified(self):
        result = evaluate(
            payload(
                sourceWidth=1920,
                sourceHeight=1080,
                outputWidth=1920,
                outputHeight=1080,
                transform="none",
                containerWidth=1920,
                containerHeight=1080,
                orientationDegrees=180,
            )
        )
        self.assertEqual(result["decision"], "native")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["preservedResults"], ["1920x1080"])
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(any("orientation 180" in item for item in result["reasons"]))

    def test_invalid_payload_raises(self):
        cases = [
            None,
            {},
            payload(transform="crop"),
            payload(transform="none"),
            payload(transform="upscale"),
            payload(orientationDegrees=45),
            payload(sourceWidth=True),
            payload(containerWidth=0),
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
