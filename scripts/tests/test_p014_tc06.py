"""TC-P014-06 source geometry is not certified by the container."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p014_tc06", Path(__file__).resolve().parents[1] / "gates" / "p014_tc06.py"
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


class TcP01406(unittest.TestCase):
    def test_module_encodes_the_case_text(self):
        self.assertEqual(
            _MODULE.INTERVENTION,
            "Provide output dimensions that differ from the source stream because of crop, "
            "reduction, or enlargement.",
        )
        self.assertEqual(
            _MODULE.EXPECTED,
            "Preserve source and output geometry separately and label transformations "
            "rather than claiming native acquisition.",
        )
        self.assertEqual(
            _MODULE.NEGATIVE,
            "Container dimensions alone must not certify source resolution.",
        )

    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P014-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIsInstance(result["reasons"], list)
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) for item in result[key]))

    def test_center_crop_preserves_both_sizes_and_rejects_container(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "transformed")
        self.assertNotEqual(result["decision"], "native")
        self.assertEqual(result["preservedResults"], ["source:4000x3000", "output:3840x2160"])
        self.assertEqual(result["rejectedClaims"], ["container-as-source"])
        self.assertTrue(any("center_crop" in item for item in result["reasons"]))
        self.assertTrue(any("orientation 90" in item for item in result["reasons"]))
        self.assertFalse(any("native" in item for item in result["reasons"]))
        self.assertNotIn("native", result["decision"])

    def test_downsample_with_matching_container_is_still_transformed(self):
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
        self.assertContract(result)
        self.assertEqual(result["decision"], "transformed")
        self.assertNotEqual(result["decision"], "native")
        self.assertEqual(result["preservedResults"], ["source:3840x2160", "output:1920x1080"])
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(any("downsample" in item for item in result["reasons"]))
        self.assertTrue(any("orientation 0" in item for item in result["reasons"]))
        self.assertFalse(any("native" in item.lower() for item in result["reasons"] + [result["decision"]]))

    def test_upscale_does_not_become_native_source(self):
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
        self.assertContract(result)
        self.assertEqual(result["decision"], "transformed")
        self.assertNotEqual(result["decision"], "native")
        self.assertEqual(result["preservedResults"], ["source:1920x1080", "output:3840x2160"])
        self.assertIn("container-as-source", result["rejectedClaims"])
        self.assertTrue(any("upscale" in item for item in result["reasons"]))
        self.assertTrue(any("orientation 180" in item for item in result["reasons"]))
        self.assertFalse(any("native" in item for item in result["reasons"]))

    def test_orientation_90_on_matching_geometry_is_native(self):
        result = evaluate(
            payload(
                sourceWidth=3840,
                sourceHeight=2160,
                outputWidth=3840,
                outputHeight=2160,
                transform="none",
                orientationDegrees=90,
                containerWidth=3840,
                containerHeight=2160,
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "native")
        self.assertIn("3840x2160", result["preservedResults"])
        self.assertEqual(result["preservedResults"], ["3840x2160"])
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(any("orientation 90" in item for item in result["reasons"]))
        self.assertTrue(any("none" in item for item in result["reasons"]))

    def test_container_mismatch_does_not_certify_matching_source(self):
        result = evaluate(
            payload(
                sourceWidth=3840,
                sourceHeight=2160,
                outputWidth=3840,
                outputHeight=2160,
                transform="none",
                orientationDegrees=90,
                containerWidth=1920,
                containerHeight=1080,
            )
        )
        self.assertContract(result)
        self.assertNotEqual(result["decision"], "native")
        self.assertEqual(result["decision"], "withheld")
        self.assertIn("container-as-source", result["rejectedClaims"])
        self.assertIn("3840x2160", result["preservedResults"])
        self.assertTrue(any("orientation 90" in item for item in result["reasons"]))
        self.assertTrue(any("container dimensions" in item for item in result["reasons"]))

    def test_center_crop_container_matching_source_has_no_container_claim(self):
        result = evaluate(
            payload(containerWidth=4000, containerHeight=3000, orientationDegrees=270)
        )
        self.assertEqual(result["decision"], "transformed")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"], ["source:4000x3000", "output:3840x2160"])
        self.assertTrue(any("center_crop" in item for item in result["reasons"]))
        self.assertTrue(any("orientation 270" in item for item in result["reasons"]))

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "transform"},
            {**valid, "extra": 1},
            {**valid, "sourceWidth": True},
            {**valid, "sourceWidth": 4000.0},
            {**valid, "sourceHeight": 0},
            {**valid, "outputHeight": -1},
            {**valid, "containerWidth": "3840"},
            {**valid, "transform": "crop"},
            {**valid, "transform": "none"},
            {**valid, "transform": "upscale"},
            {**valid, "orientationDegrees": 90.0},
            {**valid, "orientationDegrees": True},
            {**valid, "orientationDegrees": "90"},
            {
                **valid,
                "sourceWidth": 3840,
                "sourceHeight": 2160,
                "outputWidth": 3840,
                "outputHeight": 2160,
                "transform": "center_crop",
            },
            {
                **valid,
                "outputWidth": 1920,
                "outputHeight": 1080,
                "transform": "upscale",
            },
            {
                **valid,
                "outputWidth": 4096,
                "outputHeight": 2160,
                "transform": "downsample",
            },
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)

    def test_upscaled_7680_container_is_not_native_8k(self):
        result = evaluate(
            payload(
                sourceWidth=3840,
                sourceHeight=2160,
                outputWidth=7680,
                outputHeight=4320,
                transform="upscale",
                orientationDegrees=90,
                containerWidth=7680,
                containerHeight=4320,
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "transformed")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "native"})
        self.assertEqual(result["preservedResults"], ["source:3840x2160", "output:7680x4320"])
        self.assertIn("source:3840x2160", result["preservedResults"])
        self.assertIn("container-as-source", result["rejectedClaims"])
        self.assertIn("native-8k", result["rejectedClaims"])
        self.assertIn("upscaled output", result["reasons"])
        self.assertIn("cannot satisfy the native 8K acceptance requirement", result["reasons"])
        self.assertTrue(any("orientation 90" in item for item in result["reasons"]))


if __name__ == "__main__":
    unittest.main()
