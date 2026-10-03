"""TC-P032-04 codec output contradicts request."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p032_tc04", Path(__file__).resolve().parents[1] / "gates" / "p032_tc04.py"
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
        "requestedDepth": 10,
        "actualDepth": 10,
        "requestedWidth": 3840,
        "requestedHeight": 2160,
        "actualWidth": 3840,
        "actualHeight": 2160,
        "requestedTransfer": "arri-logc3-candidate",
        "actualTransfer": "arri-logc3-candidate",
        "requestedColorRange": "full",
        "actualColorRange": "full",
        "requestedTracks": ["video", "audio"],
        "actualTracks": ["video", "audio"],
        "configureSucceeded": True,
        "trustConfigureOnly": False,
        "retainedMedia": ["encoded-access-unit"],
    }
    base.update(overrides)
    return base


class TcP03204(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P032-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_eight_bit_output_after_ten_bit_request_fails_the_contract(self):
        source = payload(actualDepth=8)
        result = evaluate(source)
        self.assertContract(result)
        self.assertEqual(result["decision"], "contract_failed")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("depth", result["rejectedClaims"])
        self.assertIn("encoded-access-unit", result["preservedResults"])
        self.assertTrue(any("depth=8" in item for item in result["preservedResults"]))
        self.assertTrue(any("depth=10" in item for item in result["preservedResults"]))
        self.assertTrue(any("eight-bit output" in item for item in result["reasons"]))

    def test_wrong_color_range_metadata_fails_without_dropping_media(self):
        result = evaluate(payload(actualColorRange="limited", retainedMedia=["color-sample"]))
        self.assertContract(result)
        self.assertEqual(result["decision"], "contract_failed")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], ["color-range"])
        self.assertIn("color-sample", result["preservedResults"])
        self.assertTrue(any("color-range metadata" in item for item in result["reasons"]))

    def test_negative_configure_parameters_alone_must_fail(self):
        result = evaluate(payload(trustConfigureOnly=True, retainedMedia=["configured-buffer"]))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "output_observed"})
        self.assertIn("configure-only-trust", result["rejectedClaims"])
        self.assertIn("configured-buffer", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_matching_output_is_not_ten_bit_fidelity(self):
        result = evaluate(payload())
        self.assertEqual(result["decision"], "output_observed")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("encoded-access-unit", result["preservedResults"])
        self.assertTrue(any("not ten-bit fidelity" in item for item in result["reasons"]))

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "requestedDepth": 12},
            {**valid, "actualDepth": True},
            {**valid, "requestedTracks": []},
            {**valid, "retainedMedia": [""]},
            {**valid, "requestedColorRange": "video"},
            {**valid, "trustConfigureOnly": "yes"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
