"""TC-P061-04 P010 plane geometry fault."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p061_tc04", Path(__file__).resolve().parents[1] / "gates" / "p061_tc04.py"
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
    code = overrides.get("unpackedCode", 940)
    alignment = overrides.get("alignment", "msb")
    stored = overrides.get("storedWord", (code << 6) if alignment == "msb" else code)
    base = {
        "nominalWidth": 1920,
        "nominalHeight": 1080,
        "strideBytes": 3840,
        "crop": "none",
        "layout": "P010",
        "alignment": alignment,
        "unpackedCode": code,
        "storedWord": stored,
        "plane": "luma",
        "chromaEndpoint": False,
    }
    base.update(overrides)
    if "storedWord" not in overrides and (
        "unpackedCode" in overrides or "alignment" in overrides
    ):
        code = base["unpackedCode"]
        base["storedWord"] = (code << 6) if base["alignment"] == "msb" else code
    return base


class TcP06104(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P061-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_packet_strings(self):
        self.assertIn("nominal dimensions", _MODULE.INTERVENTION)
        self.assertEqual(
            _MODULE.NEGATIVE,
            "Writing ten-bit values into the low six-bit-aligned position must fail.",
        )
        self.assertIn("padded rows", _MODULE.REPEAT)
        self.assertIn("unsupported plane", _MODULE.REPEAT)

    def test_low_six_alignment_fails_and_keeps_nominal_size(self):
        result = evaluate(payload(alignment="low-six", storedWord=940))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("low-six-aligned", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("nominal:1920x1080", result["preservedResults"])
        self.assertIn("code:940", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "layout_checked"})

    def test_supported_msb_layout_is_checked_not_qualified(self):
        result = evaluate(payload())
        self.assertEqual(result["decision"], "layout_checked")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("nominal:1920x1080", result["preservedResults"])
        self.assertIn("stored:60160", result["preservedResults"])

    def test_repeat_padded_rows(self):
        result = evaluate(payload(layout="padded-P010", strideBytes=4096))
        self.assertEqual(result["decision"], "layout_checked")
        self.assertIn("stride:4096", result["preservedResults"])
        self.assertIn("nominal:1920x1080", result["preservedResults"])
        short = evaluate(payload(layout="padded-P010", strideBytes=3840))
        self.assertEqual(short["decision"], "rejected")
        self.assertIn("stride-bounds", short["rejectedClaims"])
        self.assertIn("nominal:1920x1080", short["preservedResults"])

    def test_repeat_chroma_endpoint(self):
        result = evaluate(payload(plane="chroma", chromaEndpoint=True, unpackedCode=64))
        self.assertEqual(result["decision"], "layout_checked")
        self.assertIn("plane:chroma", result["preservedResults"])
        self.assertIn("chroma-endpoint:true", result["preservedResults"])
        self.assertIn("code:64", result["preservedResults"])
        self.assertIn("nominal:1920x1080", result["preservedResults"])

    def test_repeat_unsupported_plane_layout(self):
        result = evaluate(payload(layout="NV12"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("unsupported-layout", result["rejectedClaims"])
        self.assertIn("nominal:1920x1080", result["preservedResults"])
        self.assertIn("layout:NV12", result["preservedResults"])

    def test_unpacked_code_mismatch_fails(self):
        result = evaluate(payload(storedWord=1))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("unpacked-code-mismatch", result["rejectedClaims"])
        self.assertIn("code:940", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "nominalWidth": 0},
            {**valid, "unpackedCode": 1024},
            {**valid, "chromaEndpoint": True},
            {**valid, "alignment": "lsb"},
            {**valid, "storedWord": True},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
