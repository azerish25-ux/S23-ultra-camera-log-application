"""TC-P028-04 configure success does not prove the emitted stream."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p028_tc04", Path(__file__).resolve().parents[1] / "gates" / "p028_tc04.py"
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
_MEDIA = "private-stage/take-p028.mp4"


def payload(**overrides):
    base = {
        "requestedDepth": 10,
        "actualDepth": 10,
        "requestedWidth": 3840,
        "requestedHeight": 2160,
        "actualWidth": 3840,
        "actualHeight": 2160,
        "requestedTransfer": "hlg",
        "actualTransfer": "hlg",
        "requestedColorRange": "full",
        "actualColorRange": "full",
        "requestedTracks": ["video", "audio"],
        "actualTracks": ["video", "audio"],
        "configureSucceeded": True,
        "trustConfigureOnly": False,
        "retainedMedia": [_MEDIA],
    }
    base.update(overrides)
    return base


class TcP02804(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P028-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_module_encodes_the_case_text(self):
        self.assertIn("selected tracks", _MODULE.INTERVENTION)
        self.assertIn("accurate status", _MODULE.EXPECTED)
        self.assertIn("configure parameters", _MODULE.NEGATIVE)

    def test_eight_bit_after_ten_bit_request_fails_the_contract(self):
        result = evaluate(payload(actualDepth=8))
        self.assertContract(result)
        self.assertEqual(result["decision"], "contract_failed")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("depth", result["rejectedClaims"])
        self.assertIn(_MEDIA, result["preservedResults"])
        self.assertTrue(any("eight-bit" in item for item in result["reasons"]))
        self.assertTrue(any("depth=8" in item for item in result["preservedResults"]))
        self.assertTrue(any("depth=10" in item for item in result["preservedResults"]))

    def test_wrong_color_range_fails_and_keeps_the_media(self):
        result = evaluate(payload(actualColorRange="limited"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "contract_failed")
        self.assertEqual(result["rejectedClaims"], ["color-range"])
        self.assertIn(_MEDIA, result["preservedResults"])
        self.assertTrue(any("color-range" in item for item in result["reasons"]))

    def test_trusting_configure_parameters_is_rejected(self):
        result = evaluate(payload(trustConfigureOnly=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "output_observed"})
        self.assertIn("configure-only-trust", result["rejectedClaims"])
        self.assertIn(_MEDIA, result["preservedResults"])

    def test_configure_only_trust_with_eight_bit_output_is_rejected(self):
        result = evaluate(payload(actualDepth=8, trustConfigureOnly=True, configureSucceeded=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("configure-only-trust", result["rejectedClaims"])
        self.assertIn("depth", result["rejectedClaims"])
        self.assertIn(_MEDIA, result["preservedResults"])

    def test_dropped_audio_track_fails_the_output_contract(self):
        result = evaluate(payload(actualTracks=["video"]))
        self.assertEqual(result["decision"], "contract_failed")
        self.assertIn("tracks", result["rejectedClaims"])
        self.assertIn(_MEDIA, result["preservedResults"])

    def test_matching_output_is_observed_not_qualified(self):
        result = evaluate(payload())
        self.assertEqual(result["decision"], "output_observed")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn(_MEDIA, result["preservedResults"])
        self.assertTrue(any("not ten-bit fidelity" in item for item in result["reasons"]))

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {**valid, "requestedDepth": 12},
            {**valid, "actualColorRange": "broadcast"},
            {**valid, "requestedTracks": ["video", "video"]},
            {**valid, "trustConfigureOnly": "true"},
            {k: v for k, v in valid.items() if k != "retainedMedia"},
            {**valid, "extra": True},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
