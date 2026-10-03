"""TC-P016-06 geometry mismatch."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p016_tc06", Path(__file__).resolve().parents[1] / "gates" / "p016_tc06.py"
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
_ORACLE = ["file-retained", "playback:separate", "cadence:separate"]


def payload(**overrides):
    base = {
        "sourceWidth": 4000,
        "sourceHeight": 3000,
        "outputWidth": 4000,
        "outputHeight": 3000,
        "transform": "none",
        "orientationDegrees": 0,
        "containerWidth": 4000,
        "containerHeight": 3000,
    }
    base.update(overrides)
    return base


class TcP01606(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P016-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertEqual(result["openQuestions"], ["not-endurance-certified"])
        for token in _ORACLE:
            self.assertIn(token, result["preservedResults"])

    def test_contract_text_is_encoded(self):
        self.assertIn("crop", _MODULE.INTERVENTION)
        self.assertIn("native acquisition", _MODULE.EXPECTED)
        self.assertIn("Container dimensions", _MODULE.NEGATIVE)

    def test_center_crop_preserves_source_and_output(self):
        result = evaluate(
            payload(
                outputWidth=1920,
                outputHeight=1080,
                transform="center_crop",
                containerWidth=1920,
                containerHeight=1080,
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "transformed")
        self.assertEqual(
            result["preservedResults"],
            ["source:4000x3000", "output:1920x1080", *_ORACLE],
        )
        self.assertIn("container-as-source", result["rejectedClaims"])
        self.assertTrue(any("center_crop" in reason for reason in result["reasons"]))
        self.assertFalse(any("native" in reason for reason in result["reasons"]))

    def test_linear_downsample_preserves_source_and_output(self):
        result = evaluate(
            payload(
                outputWidth=1920,
                outputHeight=1080,
                transform="downsample",
                containerWidth=4000,
                containerHeight=3000,
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "transformed")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("source:4000x3000", result["preservedResults"])
        self.assertIn("output:1920x1080", result["preservedResults"])
        self.assertTrue(any(reason == "transform downsample" for reason in result["reasons"]))

    def test_upscale_preserves_source_and_output(self):
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
        self.assertEqual(
            result["preservedResults"],
            ["source:1920x1080", "output:3840x2160", *_ORACLE],
        )
        self.assertIn("container-as-source", result["rejectedClaims"])
        self.assertTrue(any(reason == "transform upscale" for reason in result["reasons"]))

    def test_orientation_metadata_does_not_invent_a_new_source(self):
        result = evaluate(payload(orientationDegrees=90))
        self.assertContract(result)
        self.assertEqual(result["decision"], "native")
        self.assertEqual(result["preservedResults"], ["4000x3000", *_ORACLE])
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(any(reason == "orientation 90" for reason in result["reasons"]))
        self.assertTrue(any("4000x3000" in reason for reason in result["reasons"]))

    def test_container_dimensions_do_not_certify_source(self):
        result = evaluate(payload(containerWidth=1920, containerHeight=1080))
        self.assertContract(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertNotIn(result["decision"], {"native", "qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], ["container-as-source"])
        self.assertEqual(result["preservedResults"], ["4000x3000", *_ORACLE])
        self.assertTrue(any("must not certify source resolution" in reason for reason in result["reasons"]))
        self.assertNotIn("1920x1080", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "transform": "center_crop"},
            {**valid, "outputWidth": 1920, "transform": "none"},
            {**valid, "orientationDegrees": 90.0},
            {**valid, "sourceWidth": True},
            {**valid, "transform": "scale"},
            {**valid, "extra": 1},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
