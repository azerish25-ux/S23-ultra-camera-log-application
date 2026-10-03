"""TC-P058-03 range and matrix contradiction."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p058_tc03", Path(__file__).resolve().parents[1] / "gates" / "p058_tc03.py"
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
        "streamYuv": "BT.709",
        "sidecarYuv": "BT.709",
        "streamPrimaries": "AWG3",
        "sidecarPrimaries": "AWG3",
        "streamTransfer": "LogC3",
        "sidecarTransfer": "LogC3",
        "impliedFromYuv": False,
        "interpretationDocumented": True,
    }
    base.update(overrides)
    return base


class TcP05803(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P058-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertTrue(any(item.startswith("stream-primaries:") for item in result["preservedResults"]))

    def test_documented_agreement_is_recorded_not_qualified(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "interpretation_recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("stream-yuv:BT.709", result["preservedResults"])
        self.assertTrue(any("not treated as primaries" in item for item in result["reasons"]))

    def test_negative_rec709_yuv_does_not_imply_rec709_primaries(self):
        result = evaluate(
            payload(
                streamPrimaries="Rec.709",
                sidecarPrimaries="Rec.709",
                impliedFromYuv=True,
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("yuv-implied-primaries", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("stream-primaries:Rec.709", result["preservedResults"])
        self.assertIn("stream-yuv:BT.709", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_repeat_full_video_level_confusion(self):
        result = evaluate(payload(streamRange="full", sidecarRange="video", interpretationDocumented=False))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("range-contradiction", result["rejectedClaims"])
        self.assertIn("stream-range:full", result["preservedResults"])
        self.assertIn("sidecar-range:video", result["preservedResults"])
        self.assertIn("documented interoperable interpretation required", result["openQuestions"])

    def test_repeat_incorrect_hlg_transfer_tag(self):
        result = evaluate(payload(streamTransfer="HLG", sidecarTransfer="LogC3", interpretationDocumented=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("transfer-contradiction", result["rejectedClaims"])
        self.assertIn("stream-transfer:HLG", result["preservedResults"])
        self.assertIn("sidecar-transfer:LogC3", result["preservedResults"])
        self.assertIn("documented interpretation does not accept the contradiction", result["openQuestions"])

    def test_gamut_disagreement_keeps_both_primaries(self):
        result = evaluate(payload(streamPrimaries="AWG3", sidecarPrimaries="Rec.709"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("gamut-contradiction", result["rejectedClaims"])
        self.assertIn("stream-primaries:AWG3", result["preservedResults"])
        self.assertIn("sidecar-primaries:Rec.709", result["preservedResults"])

    def test_consistent_undocumented_metadata_is_withheld(self):
        result = evaluate(payload(interpretationDocumented=False))
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("documented interoperable interpretation required", result["openQuestions"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "streamYuv"},
            {**valid, "extra": True},
            {**valid, "streamRange": "legal"},
            {**valid, "streamYuv": "Rec.709"},
            {**valid, "impliedFromYuv": "true"},
            {**valid, "streamTransfer": "PQ"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
