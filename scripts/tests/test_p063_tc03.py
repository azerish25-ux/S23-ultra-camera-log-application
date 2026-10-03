"""TC-P063-03 range and matrix contradiction."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p063_tc03", Path(__file__).resolve().parents[1] / "gates" / "p063_tc03.py"
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
        "streamId": "logc3-main10",
        "streamRange": "video",
        "sidecarRange": "video",
        "yuvMatrix": "BT.709",
        "declaredPrimaries": "Rec.709",
        "streamTransfer": "LogC3",
        "sidecarTransfer": "LogC3",
        "primariesFromYuv": True,
        "interpretationDocumented": False,
    }
    base.update(overrides)
    return base


class TcP06303(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P063-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_packet_strings(self):
        self.assertEqual(
            _MODULE.NEGATIVE,
            "Rec.709 YUV coefficients must not imply Rec.709 RGB primaries automatically.",
        )
        self.assertEqual(
            _MODULE.EXPECTED,
            "Reject contradictory accepted metadata and require a documented interoperable interpretation.",
        )

    def test_rec709_yuv_does_not_imply_primaries(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["yuv-implies-primaries"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("yuv:BT.709", result["preservedResults"])
        self.assertIn("primaries:Rec.709", result["preservedResults"])
        self.assertIn("logc3-main10", result["preservedResults"])
        self.assertIn("a documented interoperable interpretation is required", result["openQuestions"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_repeat_full_video_level_confusion(self):
        result = evaluate(
            payload(
                primariesFromYuv=False,
                declaredPrimaries="AWG3",
                streamRange="video",
                sidecarRange="full",
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("contradictory-metadata", result["rejectedClaims"])
        self.assertIn("stream-range:video", result["preservedResults"])
        self.assertIn("sidecar-range:full", result["preservedResults"])
        self.assertNotIn("yuv-implies-primaries", result["rejectedClaims"])

    def test_repeat_incorrect_hlg_transfer_tag(self):
        result = evaluate(
            payload(
                primariesFromYuv=False,
                declaredPrimaries="AWG3",
                streamTransfer="LogC3",
                sidecarTransfer="HLG",
                interpretationDocumented=True,
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("contradictory-metadata", result["rejectedClaims"])
        self.assertIn("stream-transfer:LogC3", result["preservedResults"])
        self.assertIn("sidecar-transfer:HLG", result["preservedResults"])
        self.assertTrue(
            any("documented interpretation was recorded" in item for item in result["openQuestions"])
        )

    def test_independent_primaries_are_withheld(self):
        result = evaluate(payload(primariesFromYuv=False, declaredPrimaries="AWG3"))
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("primaries:AWG3", result["preservedResults"])
        self.assertIn("yuv:BT.709", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "yuvMatrix": "BT.601"},
            {**valid, "streamRange": "legal"},
            {**valid, "primariesFromYuv": "true"},
            {k: v for k, v in valid.items() if k != "streamId"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
