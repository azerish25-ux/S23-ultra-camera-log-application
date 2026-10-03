"""TC-P059-04 P010 plane geometry fault."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p059_tc04", Path(__file__).resolve().parents[1] / "gates" / "p059_tc04.py"
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
    code = overrides.get("unpackedCode", 512)
    base = {
        "nominalWidth": 3840,
        "nominalHeight": 2160,
        "rowStride": 3840,
        "cropX": 0,
        "cropY": 0,
        "cropW": 3840,
        "cropH": 2160,
        "planeArrangement": "Y-UV",
        "alignment": "high-six",
        "unpackedCode": code,
        "packedWord": code << 6,
        "repeat": "none",
    }
    base.update(overrides)
    if "packedWord" not in overrides and "unpackedCode" in overrides and overrides.get("alignment", "high-six") == "high-six":
        base["packedWord"] = overrides["unpackedCode"] << 6
    return base


class TcP05904(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P059-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("size:3840x2160", result["preservedResults"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_constants_encode_the_case(self):
        self.assertIn("nominal dimensions", _MODULE.INTERVENTION)
        self.assertIn("unpacked-code", _MODULE.EXPECTED)
        self.assertIn("low six-bit-aligned", _MODULE.NEGATIVE)

    def test_supported_layout_is_checked_not_qualified(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "layout_checked")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("code:512", result["preservedResults"])
        self.assertIn("word:32768", result["preservedResults"])
        self.assertIn("alignment:high-six", result["preservedResults"])
        self.assertIn("plane:Y-UV", result["preservedResults"])

    def test_negative_low_six_alignment_fails(self):
        result = evaluate(payload(alignment="low-six", packedWord=512, unpackedCode=512))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "layout_checked"})
        self.assertIn("low-six-bit-alignment", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("code:512", result["preservedResults"])
        self.assertIn("word:512", result["preservedResults"])
        self.assertIn("size:3840x2160", result["preservedResults"])

    def test_repeat_padded_rows_keep_nominal_size(self):
        result = evaluate(payload(rowStride=4096, repeat="padded-rows"))
        self.assertEqual(result["decision"], "layout_checked")
        self.assertIn("stride:4096", result["preservedResults"])
        self.assertIn("size:3840x2160", result["preservedResults"])
        self.assertIn("repeat:padded-rows", result["preservedResults"])
        self.assertEqual(result["rejectedClaims"], [])

    def test_repeat_chroma_endpoint_verifies_the_unpacked_code(self):
        result = evaluate(payload(unpackedCode=1023, repeat="chroma-endpoint"))
        self.assertEqual(result["decision"], "layout_checked")
        self.assertIn("code:1023", result["preservedResults"])
        self.assertIn(f"word:{1023 << 6}", result["preservedResults"])
        self.assertIn("repeat:chroma-endpoint", result["preservedResults"])
        self.assertIn("size:3840x2160", result["preservedResults"])

    def test_repeat_unsupported_plane_keeps_nominal_dimensions(self):
        result = evaluate(payload(planeArrangement="unsupported", repeat="unsupported-plane"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("unsupported-plane", result["rejectedClaims"])
        self.assertIn("plane:unsupported", result["preservedResults"])
        self.assertIn("size:3840x2160", result["preservedResults"])
        self.assertIn("repeat:unsupported-plane", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "layout_checked"})

    def test_crop_and_stride_and_word_faults_keep_the_code(self):
        crop = evaluate(payload(cropX=1))
        self.assertEqual(crop["decision"], "rejected")
        self.assertIn("crop-bounds", crop["rejectedClaims"])
        self.assertIn("size:3840x2160", crop["preservedResults"])
        stride = evaluate(payload(rowStride=1920))
        self.assertIn("stride-bounds", stride["rejectedClaims"])
        self.assertIn("stride:1920", stride["preservedResults"])
        word = evaluate(payload(packedWord=512))
        self.assertIn("unpacked-mismatch", word["rejectedClaims"])
        self.assertIn("code:512", word["preservedResults"])
        self.assertIn("word:512", word["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "rowStride"},
            {**valid, "extra": 1},
            {**valid, "nominalWidth": 0},
            {**valid, "alignment": "msb"},
            {**valid, "planeArrangement": "YUV"},
            {**valid, "unpackedCode": 1024},
            {**valid, "packedWord": -1},
            {**valid, "repeat": "tile"},
            {**valid, "cropX": -1},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
