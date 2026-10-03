"""TC-P009-06 geometry mismatch."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p009_tc06", Path(__file__).resolve().parents[1] / "gates" / "p009_tc06.py"
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


def geometry(**overrides):
    base = {
        "sourceWidth": 4000,
        "sourceHeight": 3000,
        "outputWidth": 3840,
        "outputHeight": 2160,
        "transform": "center_crop",
        "orientationDegrees": 90,
        "containerWidth": 3840,
        "containerHeight": 2160,
    }
    base.update(overrides)
    return base


class TcP00906(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P009-06")
        self.assertIn(result["decision"], {"transformed", "native", "withheld"})
        self.assertNotEqual(result["decision"], "allowed")
        self.assertIsInstance(result["reasons"], list)
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) for item in result[key]))

    def test_center_crop_preserves_both_geometries_and_rejects_container(self):
        result = evaluate(geometry())
        self.assertContract(result)
        self.assertEqual(result["decision"], "transformed")
        self.assertNotEqual(result["decision"], "native")
        self.assertIn("center crop", result["reasons"])
        self.assertIn("orientation 90", result["reasons"])
        self.assertEqual(
            result["preservedResults"],
            ["source:4000x3000", "output:3840x2160"],
        )
        self.assertEqual(result["rejectedClaims"], ["container-as-source"])
        self.assertNotIn("source:2160x3840", result["preservedResults"])
        self.assertNotIn("source:3840x2160", result["preservedResults"])

    def test_center_crop_with_matching_container_is_still_not_native(self):
        result = evaluate(
            geometry(containerWidth=4000, containerHeight=3000, orientationDegrees=90)
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "transformed")
        self.assertNotEqual(result["decision"], "native")
        self.assertIn("center crop", result["reasons"])
        self.assertIn("orientation 90", result["reasons"])
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(
            result["preservedResults"],
            ["source:4000x3000", "output:3840x2160"],
        )

    def test_linear_downsample_labels_reduction(self):
        result = evaluate(
            geometry(
                sourceWidth=3840,
                sourceHeight=2160,
                outputWidth=1920,
                outputHeight=1080,
                transform="downsample",
                orientationDegrees=0,
                containerWidth=1920,
                containerHeight=1080,
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "transformed")
        self.assertNotEqual(result["decision"], "native")
        self.assertIn("linear downsample", result["reasons"])
        self.assertIn("orientation 0", result["reasons"])
        self.assertNotIn("center crop", result["reasons"])
        self.assertNotIn("upscaled output", result["reasons"])
        self.assertEqual(
            result["preservedResults"],
            ["source:3840x2160", "output:1920x1080"],
        )
        self.assertEqual(result["rejectedClaims"], ["container-as-source"])

    def test_upscaled_output_labels_enlargement(self):
        result = evaluate(
            geometry(
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
        self.assertContract(result)
        self.assertEqual(result["decision"], "transformed")
        self.assertNotEqual(result["decision"], "native")
        self.assertIn("upscaled output", result["reasons"])
        self.assertIn("orientation 180", result["reasons"])
        self.assertEqual(
            result["preservedResults"],
            ["source:1920x1080", "output:3840x2160"],
        )
        self.assertIn("container-as-source", result["rejectedClaims"])

    def test_orientation_metadata_does_not_swap_native_acquisition(self):
        for degrees in (0, 90, 180, 270):
            result = evaluate(
                geometry(
                    sourceWidth=1920,
                    sourceHeight=1080,
                    outputWidth=1920,
                    outputHeight=1080,
                    transform="none",
                    orientationDegrees=degrees,
                    containerWidth=1920,
                    containerHeight=1080,
                )
            )
            self.assertContract(result)
            self.assertEqual(result["decision"], "native")
            self.assertNotEqual(result["decision"], "transformed")
            self.assertIn(f"orientation {degrees}", result["reasons"])
            self.assertIn("native acquisition", result["reasons"])
            self.assertEqual(
                result["preservedResults"],
                ["source:1920x1080", "output:1920x1080"],
            )
            self.assertNotIn("source:1080x1920", result["preservedResults"])
            self.assertEqual(result["rejectedClaims"], [])
            self.assertEqual(result["openQuestions"], [])

    def test_orientation_90_on_a_crop_does_not_become_native(self):
        result = evaluate(
            geometry(
                sourceWidth=1920,
                sourceHeight=1080,
                outputWidth=1080,
                outputHeight=1080,
                transform="center_crop",
                orientationDegrees=90,
                containerWidth=1080,
                containerHeight=1080,
            )
        )
        self.assertEqual(result["decision"], "transformed")
        self.assertNotEqual(result["decision"], "native")
        self.assertIn("center crop", result["reasons"])
        self.assertIn("orientation 90", result["reasons"])
        self.assertEqual(
            result["preservedResults"],
            ["source:1920x1080", "output:1080x1080"],
        )
        self.assertIn("container-as-source", result["rejectedClaims"])

    def test_one_axis_container_mismatch_is_not_source_resolution(self):
        result = evaluate(
            geometry(
                sourceWidth=3840,
                sourceHeight=2160,
                outputWidth=1920,
                outputHeight=1080,
                transform="downsample",
                orientationDegrees=90,
                containerWidth=3840,
                containerHeight=1080,
            )
        )
        self.assertEqual(result["decision"], "transformed")
        self.assertNotEqual(result["decision"], "native")
        self.assertIn("linear downsample", result["reasons"])
        self.assertIn("container-as-source", result["rejectedClaims"])
        self.assertIn("source:3840x2160", result["preservedResults"])
        self.assertIn("output:1920x1080", result["preservedResults"])

    def test_container_alone_does_not_certify_when_source_matches_output(self):
        result = evaluate(
            geometry(
                sourceWidth=1920,
                sourceHeight=1080,
                outputWidth=1920,
                outputHeight=1080,
                transform="none",
                orientationDegrees=90,
                containerWidth=3840,
                containerHeight=2160,
            )
        )
        self.assertContract(result)
        self.assertNotEqual(result["decision"], "native")
        self.assertEqual(result["decision"], "withheld")
        self.assertIn("orientation 90", result["reasons"])
        self.assertEqual(result["rejectedClaims"], ["container-as-source"])
        self.assertEqual(
            result["preservedResults"],
            ["source:1920x1080", "output:1920x1080"],
        )

    def test_invalid_payload_raises(self):
        valid = geometry()
        cases = [
            None,
            [],
            {},
            {"sourceWidth": 1920},
            {**valid, "extra": 1},
            {k: v for k, v in valid.items() if k != "transform"},
            {**valid, "sourceWidth": 0},
            {**valid, "sourceHeight": -1},
            {**valid, "outputWidth": True},
            {**valid, "outputHeight": 1080.0},
            {**valid, "outputWidth": "3840"},
            {**valid, "containerWidth": None},
            {**valid, "containerHeight": False},
            {**valid, "transform": "crop"},
            {**valid, "transform": "center crop"},
            {**valid, "transform": "NONE"},
            {**valid, "transform": None},
            {**valid, "orientationDegrees": 90.0},
            {**valid, "orientationDegrees": "90"},
            {**valid, "orientationDegrees": True},
            {**valid, "orientationDegrees": None},
        ]
        for payload in cases:
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    evaluate(payload)


if __name__ == "__main__":
    unittest.main()
