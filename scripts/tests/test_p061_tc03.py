"""TC-P061-03 range and matrix contradiction."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p061_tc03", Path(__file__).resolve().parents[1] / "gates" / "p061_tc03.py"
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
        "sidecarRange": "video",
        "streamRange": "video",
        "sidecarMatrix": "BT.709",
        "streamMatrix": "BT.709",
        "sidecarTransfer": "Rec.709",
        "streamTransfer": "Rec.709",
        "sidecarGamut": "Rec.709",
        "streamGamut": "Rec.709",
        "documentedInterpretation": "",
        "inferPrimariesFromYuv": False,
    }
    base.update(overrides)
    return base


class TcP06103(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P061-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_packet_strings(self):
        self.assertIn("YUV matrix", _MODULE.INTERVENTION)
        self.assertEqual(
            _MODULE.NEGATIVE,
            "Rec.709 YUV coefficients must not imply Rec.709 RGB primaries automatically.",
        )
        self.assertIn("full/video", _MODULE.REPEAT)
        self.assertIn("HLG", _MODULE.REPEAT)

    def test_rec709_yuv_does_not_imply_primaries(self):
        result = evaluate(payload(inferPrimariesFromYuv=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["yuv-not-rgb-primaries"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("sidecar:video/BT.709/Rec.709/Rec.709", result["preservedResults"])
        self.assertIn("stream:video/BT.709/Rec.709/Rec.709", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "withheld"})

    def test_agreement_without_inference_is_not_qualification(self):
        result = evaluate(payload())
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("interpretation:absent", result["preservedResults"])

    def test_repeat_full_video_level_confusion(self):
        result = evaluate(payload(sidecarRange="full", streamRange="video"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("contradictory-metadata", result["rejectedClaims"])
        self.assertIn("sidecar:full/BT.709/Rec.709/Rec.709", result["preservedResults"])
        self.assertIn("stream:video/BT.709/Rec.709/Rec.709", result["preservedResults"])
        self.assertIn("documented interoperable interpretation required", result["openQuestions"])

    def test_repeat_incorrect_hlg_transfer_tag(self):
        result = evaluate(
            payload(
                sidecarTransfer="HLG",
                streamTransfer="Rec.709",
                sidecarGamut="Rec.2020",
                streamGamut="Rec.2020",
                sidecarMatrix="BT.2020",
                streamMatrix="BT.2020",
                documentedInterpretation="hlg-video-not-rec709",
            )
        )
        self.assertEqual(result["decision"], "interpretation_required")
        self.assertIn("contradictory-metadata", result["rejectedClaims"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("interpretation:hlg-video-not-rec709", result["preservedResults"])
        self.assertIn("sidecar:video/BT.2020/HLG/Rec.2020", result["preservedResults"])
        self.assertIn("stream:video/BT.2020/Rec.709/Rec.2020", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "sidecarRange": "legal"},
            {**valid, "inferPrimariesFromYuv": "yes"},
            {**valid, "documentedInterpretation": "has space"},
            {k: v for k, v in valid.items() if k != "streamGamut"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
