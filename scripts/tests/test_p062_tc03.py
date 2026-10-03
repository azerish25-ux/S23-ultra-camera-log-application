"""TC-P062-03 range and matrix contradiction."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p062_tc03", Path(__file__).resolve().parents[1] / "gates" / "p062_tc03.py"
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
        "sampleId": "sidecar-a",
        "sidecarRange": "full",
        "streamRange": "video",
        "sidecarMatrix": "bt709",
        "streamMatrix": "bt709",
        "sidecarTransfer": "bt709",
        "streamTransfer": "bt709",
        "sidecarGamut": "bt709",
        "streamGamut": "bt709",
        "yuvImpliesRgb": False,
        "interpretation": "",
    }
    base.update(overrides)
    return base


class TcP06203(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P062-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_packet_strings(self):
        self.assertEqual(
            _MODULE.NEGATIVE,
            "Rec.709 YUV coefficients must not imply Rec.709 RGB primaries automatically.",
        )

    def test_repeat_full_video_level_confusion(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["contradictory-metadata"])
        self.assertIn("range:full/video", result["preservedResults"])
        self.assertIn("matrix:bt709/bt709", result["preservedResults"])
        self.assertIn("sidecar-a", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_repeat_incorrect_hlg_transfer_tag(self):
        result = evaluate(
            payload(
                sampleId="hlg-tag",
                sidecarRange="video",
                streamRange="video",
                sidecarTransfer="hlg",
                streamTransfer="bt709",
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("contradictory-metadata", result["rejectedClaims"])
        self.assertIn("transfer:hlg/bt709", result["preservedResults"])
        self.assertIn("range:video/video", result["preservedResults"])
        self.assertIn("hlg-tag", result["preservedResults"])

    def test_rec709_yuv_does_not_imply_rgb_primaries(self):
        result = evaluate(
            payload(
                sidecarRange="video",
                streamRange="video",
                sidecarGamut="bt709",
                streamGamut="bt2020",
                yuvImpliesRgb=True,
                interpretation="bt709-video",
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(
            result["rejectedClaims"],
            ["contradictory-metadata", "rec709-yuv-implies-rgb"],
        )
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("gamut:bt709/bt2020", result["preservedResults"])
        self.assertIn("interpretation:bt709-video", result["preservedResults"])

    def test_implication_fails_even_when_tags_match(self):
        result = evaluate(
            payload(sidecarRange="video", streamRange="video", yuvImpliesRgb=True, interpretation="same")
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["rec709-yuv-implies-rgb"])
        self.assertIn("matrix:bt709/bt709", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "interpretation_documented"})

    def test_consistent_tags_need_a_documented_interpretation(self):
        agreed = payload(sidecarRange="video", streamRange="video")
        missing = evaluate(agreed)
        self.assertEqual(missing["decision"], "withheld")
        self.assertEqual(missing["rejectedClaims"], [])
        self.assertIn("interpretation:missing", missing["preservedResults"])
        documented = evaluate({**agreed, "interpretation": "bt709-video-limited"})
        self.assertEqual(documented["decision"], "interpretation_documented")
        self.assertIn("interpretation:bt709-video-limited", documented["preservedResults"])
        self.assertNotIn(documented["decision"], {"qualified", "allowed"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "sidecarRange"},
            {**valid, "extra": True},
            {**valid, "yuvImpliesRgb": "true"},
            {**valid, "sidecarTransfer": "logc3"},
            {**valid, "interpretation": "Has Space"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
