"""TC-P064-03 range and matrix contradiction."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p064_tc03", Path(__file__).resolve().parents[1] / "gates" / "p064_tc03.py"
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
        "streamRange": "video",
        "sidecarRange": "video",
        "streamMatrix": "BT.709",
        "sidecarMatrix": "BT.709",
        "streamTransfer": "Rec.709",
        "sidecarTransfer": "Rec.709",
        "streamGamut": "Rec.709",
        "sidecarGamut": "Rec.709",
        "impliedPrimariesFromYuv": False,
        "documentedInterpretation": False,
    }
    base.update(overrides)
    return base


class TcP06403(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P064-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_packet_strings(self):
        self.assertEqual(
            _MODULE.NEGATIVE,
            "Rec.709 YUV coefficients must not imply Rec.709 RGB primaries automatically.",
        )
        self.assertIn("full/video", _MODULE.REPEAT)
        self.assertIn("HLG", _MODULE.REPEAT)

    def test_agreement_is_withheld(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("streamMatrix:BT.709", result["preservedResults"])
        self.assertIn("streamGamut:Rec.709", result["preservedResults"])

    def test_rec709_yuv_does_not_imply_rgb_primaries(self):
        result = evaluate(payload(impliedPrimariesFromYuv=True, documentedInterpretation=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["rec709-yuv-not-rgb-primaries"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("streamMatrix:BT.709", result["preservedResults"])
        self.assertIn("streamGamut:Rec.709", result["preservedResults"])
        self.assertIn("sidecarGamut:Rec.709", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "interpretation_required"})

    def test_repeat_full_video_level_confusion(self):
        result = evaluate(payload(streamRange="full", sidecarRange="video"))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["range-contradiction"])
        self.assertIn("streamRange:full", result["preservedResults"])
        self.assertIn("sidecarRange:video", result["preservedResults"])
        documented = evaluate(
            payload(streamRange="full", sidecarRange="video", documentedInterpretation=True)
        )
        self.assertEqual(documented["decision"], "interpretation_required")
        self.assertIn("range-contradiction", documented["rejectedClaims"])
        self.assertNotIn(documented["decision"], {"qualified", "allowed"})
        self.assertIn("streamRange:full", documented["preservedResults"])

    def test_repeat_incorrect_hlg_transfer_tag(self):
        result = evaluate(payload(streamTransfer="Rec.709", sidecarTransfer="HLG"))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["transfer-contradiction"])
        self.assertIn("streamTransfer:Rec.709", result["preservedResults"])
        self.assertIn("sidecarTransfer:HLG", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "streamRange": "legal"},
            {**valid, "impliedPrimariesFromYuv": "true"},
            {**valid, "streamGamut": "BT.709"},
            {k: v for k, v in valid.items() if k != "streamMatrix"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
