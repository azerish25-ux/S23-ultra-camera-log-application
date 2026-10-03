"""TC-P060-03 range and matrix contradiction."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p060_tc03", Path(__file__).resolve().parents[1] / "gates" / "p060_tc03.py"
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
        "sidecarRange": "limited",
        "streamRange": "limited",
        "sidecarMatrix": "bt709",
        "streamMatrix": "bt709",
        "sidecarTransfer": "bt709",
        "streamTransfer": "bt709",
        "sidecarGamut": "bt709",
        "streamGamut": "bt709",
        "inferPrimariesFromYuv": False,
        "documentedInterpretation": "",
    }
    base.update(overrides)
    return base


class TcP06003(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P060-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.EXPECTED, result["reasons"])
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])

    def test_packet_strings(self):
        self.assertIn("Rec.709", _MODULE.NEGATIVE)
        self.assertIn("full/video", _MODULE.REPEAT)

    def test_consistent_tags_without_interpretation_are_withheld(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("conflicts:none", result["preservedResults"])
        self.assertIn("interpretation:missing", result["preservedResults"])

    def test_documented_interpretation_is_recorded(self):
        result = evaluate(payload(documentedInterpretation="bt709-limited-video"))
        self.assertEqual(result["decision"], "interpretation_recorded")
        self.assertIn("interpretation:bt709-limited-video", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_yuv_coefficients_do_not_imply_primaries(self):
        result = evaluate(payload(inferPrimariesFromYuv=True, documentedInterpretation="bt709-limited-video"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("yuv-does-not-imply-primaries", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("matrix:bt709|bt709", result["preservedResults"])
        self.assertIn("gamut:bt709|bt709", result["preservedResults"])

    def test_repeat_full_video_level_confusion(self):
        result = evaluate(payload(sidecarRange="full", streamRange="limited"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("contradictory-metadata", result["rejectedClaims"])
        self.assertIn("range:full|limited", result["preservedResults"])
        self.assertIn("conflicts:range", result["preservedResults"])

    def test_repeat_incorrect_hlg_transfer_tag(self):
        result = evaluate(payload(sidecarTransfer="hlg", streamTransfer="bt709"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("transfer:hlg|bt709", result["preservedResults"])
        self.assertIn("conflicts:transfer", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "interpretation_recorded"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {**valid, "sidecarMatrix": "rec709"},
            {**valid, "inferPrimariesFromYuv": 1},
            {**valid, "documentedInterpretation": "Has Space"},
            {k: v for k, v in valid.items() if k != "streamGamut"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
