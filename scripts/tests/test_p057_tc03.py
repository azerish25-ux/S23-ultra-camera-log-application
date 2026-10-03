"""TC-P057-03 contradictory range, matrix, transfer, and primaries."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p057_tc03", Path(__file__).resolve().parents[1] / "gates" / "p057_tc03.py"
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
        "sidecarRange": "full",
        "streamRange": "full",
        "yuvMatrix": "rec709",
        "rgbPrimaries": "awg3",
        "sidecarTransfer": "logc3",
        "streamTransfer": "logc3",
        "inferPrimariesFromYuv": False,
    }
    base.update(overrides)
    return base


class TcP05703(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P057-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_rec709_yuv_does_not_imply_rec709_primaries(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("rec709-yuv-does-not-imply-rec709-rgb", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("primaries:awg3", result["preservedResults"])
        self.assertIn("yuv:rec709", result["preservedResults"])

    def test_repeat_full_video_range_confusion(self):
        result = evaluate(
            payload(
                sidecarRange="full",
                streamRange="video",
                yuvMatrix="identity",
                rgbPrimaries="awg3",
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("range-contradiction", result["rejectedClaims"])
        self.assertIn("sidecar-range:full", result["preservedResults"])
        self.assertIn("stream-range:video", result["preservedResults"])
        self.assertTrue(any("interoperable interpretation" in item for item in result["openQuestions"]))

    def test_repeat_incorrect_hlg_transfer_tag(self):
        result = evaluate(
            payload(
                yuvMatrix="identity",
                rgbPrimaries="awg3",
                sidecarTransfer="logc3",
                streamTransfer="hlg",
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["transfer-contradiction"])
        self.assertIn("stream-transfer:hlg", result["preservedResults"])
        self.assertIn("sidecar-transfer:logc3", result["preservedResults"])

    def test_inferring_primaries_is_rejected_even_when_tags_match(self):
        result = evaluate(
            payload(
                yuvMatrix="rec709",
                rgbPrimaries="rec709",
                inferPrimariesFromYuv=True,
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("inferred-primaries", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("primaries:rec709", result["preservedResults"])

    def test_consistent_explicit_tags_stay_withheld(self):
        result = evaluate(
            payload(yuvMatrix="identity", rgbPrimaries="awg3", inferPrimariesFromYuv=False)
        )
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("primaries:awg3", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {**valid, "sidecarRange": "legal"},
            {**valid, "streamTransfer": "pq"},
            {**valid, "inferPrimariesFromYuv": "false"},
            {k: v for k, v in valid.items() if k != "yuvMatrix"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
