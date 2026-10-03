"""TC-P059-03 range and matrix contradiction."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p059_tc03", Path(__file__).resolve().parents[1] / "gates" / "p059_tc03.py"
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
        "rangeSidecar": "video",
        "rangeStream": "video",
        "yuvMatrix": "bt709",
        "rgbGamut": "bt709",
        "transferSidecar": "bt709",
        "transferStream": "bt709",
        "inferRgbFromYuv": False,
        "interpretation": "documented",
        "repeat": "none",
    }
    base.update(overrides)
    return base


class TcP05903(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P059-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])
        self.assertIn("yuv-matrix:bt709", result["preservedResults"])

    def test_constants_encode_the_case(self):
        self.assertIn("RGB gamut", _MODULE.INTERVENTION)
        self.assertIn("documented interoperable interpretation", _MODULE.EXPECTED)
        self.assertIn("Rec.709", _MODULE.NEGATIVE)

    def test_documented_agreement_is_withheld(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("interpretation:documented", result["preservedResults"])
        self.assertIn("range-sidecar:video", result["preservedResults"])

    def test_negative_rec709_yuv_does_not_imply_rgb_primaries(self):
        result = evaluate(payload(inferRgbFromYuv=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "withheld"})
        self.assertEqual(result["rejectedClaims"], ["yuv-implies-rgb"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("rgb-gamut:bt709", result["preservedResults"])
        self.assertIn("yuv-matrix:bt709", result["preservedResults"])

    def test_repeat_full_video_level_confusion(self):
        result = evaluate(payload(rangeSidecar="full", rangeStream="video", repeat="full-video"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("range-contradiction", result["rejectedClaims"])
        self.assertIn("range-sidecar:full", result["preservedResults"])
        self.assertIn("range-stream:video", result["preservedResults"])
        self.assertIn("repeat:full-video", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_repeat_incorrect_hlg_transfer_tag(self):
        result = evaluate(
            payload(transferSidecar="bt709", transferStream="hlg", repeat="incorrect-hlg")
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("transfer-contradiction", result["rejectedClaims"])
        self.assertIn("transfer-sidecar:bt709", result["preservedResults"])
        self.assertIn("transfer-stream:hlg", result["preservedResults"])
        self.assertIn("repeat:incorrect-hlg", result["preservedResults"])

    def test_matrix_gamut_disagreement_and_missing_interpretation(self):
        result = evaluate(payload(rgbGamut="bt2020", interpretation="missing"))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(
            result["rejectedClaims"],
            ["matrix-gamut-contradiction", "interpretation-missing"],
        )
        self.assertIn("rgb-gamut:bt2020", result["preservedResults"])
        self.assertIn("yuv-matrix:bt709", result["preservedResults"])

    def test_missing_interpretation_alone_is_rejected(self):
        result = evaluate(payload(interpretation="missing"))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["interpretation-missing"])
        self.assertIn("transfer-stream:bt709", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "repeat"},
            {**valid, "extra": False},
            {**valid, "rangeSidecar": "legal"},
            {**valid, "inferRgbFromYuv": "true"},
            {**valid, "rgbGamut": "p3"},
            {**valid, "repeat": "hlg"},
            {**valid, "interpretation": "assumed"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
