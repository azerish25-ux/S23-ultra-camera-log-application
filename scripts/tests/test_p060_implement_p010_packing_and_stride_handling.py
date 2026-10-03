"""Host checks for the P060 P010 packing fixture. Not a physical S23 probe.

TC-P060-01..08 are specified in separate modules and are not executed here.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "gates"))

from p060_implement_p010_packing_and_stride_handling import (  # noqa: E402
    BASE_REVISION,
    CASE_ID,
    FIXTURE,
    HOST_LIMIT,
    MAP_ID,
    METHOD,
    MUTANT,
    MUTANT_STORE,
    ORACLE,
    assess,
    formula_endpoints,
    independent_unpack,
    independent_unpack_word,
    pack_lsb,
    pack_msb,
    quantize_chroma_limited,
    quantize_luma_limited,
    validate_document,
    write_planes,
    _load_planes,
)


RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
LUMA = ["64", "940", "64", "940", "940", "64", "940", "64"]
CHROMA = ["64", "512", "960", "512"]


def load_document() -> dict:
    path = ROOT / "docs" / "P060_IMPLEMENT_P010_PACKING_AND_STRIDE_HANDLING.json"
    return json.loads(path.read_text(encoding="utf-8"))


class P060PackingTests(unittest.TestCase):
    def assert_result(self, result) -> None:
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], "P060")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) and item for item in result[key]))

    def test_constants_encode_method_fixture_oracle_and_mutant(self) -> None:
        self.assertEqual(CASE_ID, "P060")
        self.assertEqual(MAP_ID, "s23-p010-packing-fixture")
        self.assertEqual(BASE_REVISION, "d4deac8fc82832fd23396a01065c5f0bf9da6670")
        self.assertIn("row strides", METHOD)
        self.assertIn("pixel strides", METHOD)
        self.assertIn("crop rectangles", METHOD)
        self.assertIn("not guessed", METHOD)
        self.assertEqual(FIXTURE, "Padded luma and chroma rows with known endpoint codes and a nonzero crop rectangle.")
        self.assertIn("guard bytes", ORACLE)
        self.assertEqual(MUTANT, "Store ten-bit codes in the low bits of each sixteen-bit word.")
        self.assertEqual(quantize_luma_limited("0"), 64)
        self.assertEqual(quantize_luma_limited("1"), 940)
        self.assertEqual(quantize_chroma_limited("0"), 512)
        self.assertEqual(quantize_chroma_limited("-0.5"), 64)
        self.assertEqual(quantize_chroma_limited("0.5"), 960)
        self.assertNotEqual(quantize_luma_limited("0"), quantize_chroma_limited("0"))
        self.assertEqual(formula_endpoints()["lumaWhite"], "940")
        self.assertEqual(pack_msb(64), 4096)
        self.assertEqual(pack_lsb(64), 64)
        self.assertNotEqual(pack_msb(64), pack_lsb(64))
        self.assertEqual(independent_unpack_word(pack_msb(940)), 940)
        self.assertNotEqual(independent_unpack_word(pack_lsb(940)), 940)

    def test_fixture_round_trip_keeps_padding_and_guards(self) -> None:
        raw = load_document()
        self.assertIsNone(validate_document(raw))
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P060")
        self.assertEqual(raw["mapId"], MAP_ID)
        self.assertEqual(raw["implementationBaseRevision"], BASE_REVISION)
        self.assertEqual(raw["method"], METHOD)
        self.assertEqual(raw["fixture"], FIXTURE)
        self.assertEqual(raw["oracle"], ORACLE)
        self.assertEqual(raw["mutant"], MUTANT)
        self.assertEqual(raw["planes"]["cropLeft"], "2")
        self.assertEqual(raw["planes"]["cropTop"], "2")
        self.assertGreater(int(raw["planes"]["yRowStride"]), int(raw["planes"]["bufferWidth"]) * 2)
        geometry = _load_planes(raw)
        luma = [int(item) for item in raw["lumaSamples"]]
        chroma = [int(item) for item in raw["chromaSamples"]]
        ybuf, uvbuf = write_planes(geometry, luma, chroma, "msb")
        self.assertEqual(independent_unpack(ybuf, uvbuf, geometry), (luma, chroma))
        self.assertEqual(ybuf[44], 0x00)
        self.assertEqual(ybuf[45], 0x10)
        self.assertEqual(ybuf[56], 165)
        self.assertEqual(uvbuf[0], 165)
        self.assertEqual(ybuf[0], 165)
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "geometry_retained")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("crop:2,2,6,4", result["preservedResults"])
        self.assertIn("buffer:8x4", result["preservedResults"])
        self.assertIn("y-stride:20/2", result["preservedResults"])
        self.assertIn("uv-stride:20/4", result["preservedResults"])
        self.assertIn("intended-luma:" + ",".join(LUMA), result["preservedResults"])
        self.assertIn("intended-chroma:" + ",".join(CHROMA), result["preservedResults"])
        self.assertIn("unpacked-luma:" + ",".join(LUMA), result["preservedResults"])
        self.assertIn("unpacked-chroma:" + ",".join(CHROMA), result["preservedResults"])
        self.assertIn("guards-untouched:yes", result["preservedResults"])
        self.assertIn("padding-untouched:yes", result["preservedResults"])
        self.assertIn("row-padding-y:4", result["preservedResults"])
        self.assertIn("row-padding-uv:4", result["preservedResults"])
        self.assertIn("packed-luma-0:4096", result["preservedResults"])
        self.assertIn("luma-black:64", result["preservedResults"])
        self.assertIn("luma-white:940", result["preservedResults"])
        self.assertIn("chroma-low:64", result["preservedResults"])
        self.assertIn("chroma-neutral:512", result["preservedResults"])
        self.assertIn("chroma-high:960", result["preservedResults"])
        self.assertIn(ORACLE, result["reasons"])
        self.assertIn(HOST_LIMIT, result["reasons"])
        self.assertNotIn(MUTANT, result["reasons"])
        self.assertNotIn("low-bit-ten-bit-store", result["rejectedClaims"])

    def test_mutant_low_bits_are_rejected_and_not_the_declared_path(self) -> None:
        raw = load_document()
        honest = assess(raw)
        mutant = assess(raw, store=MUTANT_STORE)
        self.assertEqual(honest["decision"], "geometry_retained")
        self.assertIn("packed-luma-0:4096", honest["preservedResults"])
        self.assert_result(mutant)
        self.assertEqual(mutant["decision"], "rejected")
        self.assertIn("low-bit-ten-bit-store", mutant["rejectedClaims"])
        self.assertIn("unpacked-code-mismatch", mutant["rejectedClaims"])
        self.assertNotIn(mutant["decision"], {"qualified", "allowed", "geometry_retained"})
        self.assertIn("intended-luma:" + ",".join(LUMA), mutant["preservedResults"])
        self.assertIn("intended-chroma:" + ",".join(CHROMA), mutant["preservedResults"])
        self.assertIn("packed-luma-0:64", mutant["preservedResults"])
        self.assertIn("unpacked-luma:1,14,1,14,14,1,14,1", mutant["preservedResults"])
        self.assertIn("guards-untouched:yes", mutant["preservedResults"])
        self.assertIn("padding-untouched:yes", mutant["preservedResults"])
        self.assertIn(MUTANT, mutant["reasons"])
        self.assertNotEqual(
            [item for item in honest["preservedResults"] if item.startswith("packed-luma-0:")],
            [item for item in mutant["preservedResults"] if item.startswith("packed-luma-0:")],
        )

    def test_unknown_plane_is_rejected_without_a_contiguous_guess(self) -> None:
        raw = load_document()
        raw["planes"]["chromaLayout"] = "contiguous-guess"
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("unknown-plane-configuration", result["rejectedClaims"])
        self.assertIn("unpacked:not-guessed", result["preservedResults"])
        self.assertIn("intended-luma:" + ",".join(LUMA), result["preservedResults"])
        self.assertIn("crop:2,2,6,4", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "geometry_retained"})
        self.assertTrue(any("not guessed" in item for item in result["reasons"]))
        self.assertTrue(any("not guessed" in item for item in result["openQuestions"]))

    def test_bounds_failure_preserves_the_inventory(self) -> None:
        raw = load_document()
        raw["planes"]["yRowStride"] = "14"
        result = assess(raw)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("luma-row-overflow", result["rejectedClaims"])
        self.assertIn("missing-row-padding", result["rejectedClaims"])
        self.assertIn("unpacked:not-guessed", result["preservedResults"])
        self.assertIn("intended-chroma:" + ",".join(CHROMA), result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "geometry_retained"})

    def test_swapped_endpoints_do_not_share_a_quantizer(self) -> None:
        raw = load_document()
        raw["endpoints"]["lumaBlack"] = "512"
        result = assess(raw)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("quantizer-not-distinct", result["rejectedClaims"])
        self.assertIn("luma-black:512", result["preservedResults"])
        self.assertIn("chroma-neutral:512", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "geometry_retained"})

    def test_invalid_documents_raise(self) -> None:
        valid = load_document()
        odd = copy.deepcopy(valid)
        odd["planes"]["cropLeft"] = "1"
        full = copy.deepcopy(valid)
        full["planes"]["cropLeft"] = "0"
        full["planes"]["cropTop"] = "0"
        full["planes"]["cropRight"] = "8"
        full["planes"]["cropBottom"] = "4"
        full["lumaSamples"] = ["64"] * 32
        full["chromaSamples"] = ["512"] * 16
        extra = copy.deepcopy(valid)
        extra["note"] = "device"
        missing = copy.deepcopy(valid)
        del missing["mutant"]
        bad_phase = copy.deepcopy(valid)
        bad_phase["phase"] = "P059"
        lsb = copy.deepcopy(valid)
        lsb["planes"]["store"] = "lsb"
        short = copy.deepcopy(valid)
        short["lumaSamples"] = ["64"]
        cases = (None, [], {}, extra, missing, bad_phase, odd, full, lsb, short)
        for sample in cases:
            with self.subTest(sample=type(sample).__name__):
                with self.assertRaises(ValueError):
                    validate_document(sample)
        with self.assertRaises(ValueError):
            assess(valid, store="low")


if __name__ == "__main__":
    unittest.main()
