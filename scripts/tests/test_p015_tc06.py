"""TC-P015-06 container dimensions do not certify source resolution."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p015_tc06", Path(__file__).resolve().parents[1] / "gates" / "p015_tc06.py"
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
        "orientationDegrees": 0,
        "containerWidth": 3840,
        "containerHeight": 2160,
    }
    base.update(overrides)
    return base


class TcP01506(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P015-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "native"})
        self.assertTrue(result["reasons"])

    def test_contract_text(self):
        self.assertIn("crop, reduction, or enlargement", _MODULE.INTERVENTION)
        self.assertIn("native acquisition", _MODULE.EXPECTED)
        self.assertIn("Container dimensions", _MODULE.NEGATIVE)
        self.assertIn("linear downsample", _MODULE.REPEAT)

    def test_center_crop_preserves_source_and_output(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "transformed")
        self.assertEqual(
            result["preservedResults"],
            ["source:4000x3000", "output:3840x2160"],
        )
        self.assertIn("container-as-source", result["rejectedClaims"])
        self.assertTrue(any("labelled" in item for item in result["reasons"]))
        self.assertNotIn("native", result["decision"])

    def test_linear_downsample_is_labelled(self):
        result = evaluate(
            payload(
                sourceWidth=3840,
                sourceHeight=2160,
                outputWidth=1920,
                outputHeight=1080,
                transform="linear_downsample",
                containerWidth=1920,
                containerHeight=1080,
            )
        )
        self.assertEqual(result["decision"], "transformed")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "native"})
        self.assertIn("source:3840x2160", result["preservedResults"])
        self.assertIn("output:1920x1080", result["preservedResults"])
        self.assertIn("container-as-source", result["rejectedClaims"])
        self.assertTrue(any("linear_downsample" in item for item in result["reasons"]))

    def test_upscale_does_not_certify_source_from_container(self):
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
        self.assertEqual(result["decision"], "transformed")
        self.assertIn("source:1920x1080", result["preservedResults"])
        self.assertIn("output:3840x2160", result["preservedResults"])
        self.assertIn("container-as-source", result["rejectedClaims"])
        self.assertNotEqual(result["preservedResults"][0], "source:3840x2160")

    def test_orientation_metadata_is_labelled(self):
        result = evaluate(
            payload(
                sourceWidth=1920,
                sourceHeight=1080,
                outputWidth=1920,
                outputHeight=1080,
                transform="none",
                orientationDegrees=90,
                containerWidth=1920,
                containerHeight=1080,
            )
        )
        self.assertEqual(result["decision"], "transformed")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "native", "untransformed"})
        self.assertIn("source:1920x1080", result["preservedResults"])
        self.assertIn("output:1920x1080", result["preservedResults"])
        self.assertIn("orientation:90", result["preservedResults"])
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(any("orientation metadata 90" in item for item in result["reasons"]))

    def test_container_alone_does_not_certify_source(self):
        result = evaluate(
            payload(
                outputWidth=4000,
                outputHeight=3000,
                transform="none",
                containerWidth=1920,
                containerHeight=1080,
            )
        )
        self.assertEqual(result["decision"], "withheld")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "native", "untransformed"})
        self.assertIn("container-as-source", result["rejectedClaims"])
        self.assertEqual(
            result["preservedResults"],
            ["source:4000x3000", "output:4000x3000"],
        )

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "transform": "scale"},
            {**valid, "orientationDegrees": 45},
            {**valid, "sourceWidth": True},
            {**valid, "transform": "none"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
