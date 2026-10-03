"""Host checks for the P035 packed RAW fixture. Not a physical S23 probe.

TC-P035-01..08 are specified in separate modules and are not executed here.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "gates"))

from p035_implement_packed_raw_decoding_fixtures import (  # noqa: E402
    BASE_REVISION,
    CASE_ID,
    FIXTURE,
    MAP_ID,
    METHOD,
    MUTANT,
    ORACLE,
    assess,
    channel_at,
    decode_plane,
    decode_row,
    inventory,
    layouts_equivalent,
    mutant_plane,
    pack_plane,
    payload_length,
    reject_mutant,
    validate_document,
)


RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
RAW10_CODES = "0,1023,0,1023,1023,0,1023,0,0,1023,0,1023,1023,0,1023,0"


def load_document() -> dict:
    return json.loads(
        (ROOT / "docs" / "P035_IMPLEMENT_PACKED_RAW_DECODING_FIXTURES.json").read_text(
            encoding="utf-8"
        )
    )


class P035PackedRawTests(unittest.TestCase):
    def assert_result(self, result) -> None:
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], "P035")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))

    def test_constants_encode_method_fixture_oracle_and_mutant(self) -> None:
        self.assertEqual(CASE_ID, "P035")
        self.assertEqual(MAP_ID, "s23-packed-raw-fixture")
        self.assertEqual(BASE_REVISION, "d4deac8fc82832fd23396a01065c5f0bf9da6670")
        self.assertIn("RAW_SENSOR, RAW10, and RAW12", METHOD)
        self.assertIn("independent bit-level references", METHOD)
        self.assertEqual(
            FIXTURE,
            "Alternating minimum and maximum sample codes in padded rows with a crop beginning "
            "on an odd coordinate.",
        )
        self.assertEqual(
            ORACLE,
            "Decoded codes and CFA coordinates match the independent fixture exactly, "
            "with padding untouched.",
        )
        self.assertEqual(
            MUTANT,
            "Read every source as contiguous sixteen-bit native-endian samples.",
        )

    def test_fixture_decodes_every_format_and_cfa_parity(self) -> None:
        raw = load_document()
        self.assertIsNone(validate_document(raw))
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P035")
        self.assertEqual(raw["implementationBaseRevision"], BASE_REVISION)
        self.assertEqual(len(raw["mosaics"]), 12)
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "decoded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"], inventory(raw["mosaics"]))
        self.assertIn("codes:raw10-rggb:" + RAW10_CODES, result["preservedResults"])
        self.assertIn("pad:raw10-rggb:5a5a5a", result["preservedResults"])
        self.assertIn("pad:raw-sensor-bggr:a5a5a5a5", result["preservedResults"])
        self.assertIn("pad:raw12-grbg:b6b6", result["preservedResults"])
        self.assertIn("channels:raw-sensor-rggb:B,G,G,R", result["preservedResults"])
        self.assertIn("channels:raw10-grbg:G,B,R,G", result["preservedResults"])
        self.assertIn("channels:raw12-gbrg:G,R,B,G", result["preservedResults"])
        self.assertIn("channels:raw12-bggr:R,G,G,B", result["preservedResults"])
        self.assertIn("crop:raw10-rggb:1,1", result["preservedResults"])
        self.assertEqual(
            result["openQuestions"],
            [
                "physical S23 capture unverified",
                "no demosaic applied",
                "no color transform applied",
            ],
        )
        self.assertIn(ORACLE, result["reasons"])
        self.assertTrue(any("not physical S23 qualification" in item for item in result["reasons"]))
        self.assertNotIn("65280", "".join(result["preservedResults"]))
        self.assertNotIn("42405", "".join(result["preservedResults"]))

    def test_mutant_contiguous_uint16_is_rejected(self) -> None:
        raw = load_document()
        mutant = reject_mutant(raw)
        self.assert_result(mutant)
        self.assertEqual(mutant["decision"], "rejected")
        self.assertNotIn(mutant["decision"], {"qualified", "allowed", "decoded"})
        self.assertEqual(mutant["rejectedClaims"], ["contiguous-sixteen-bit-native-endian"])
        self.assertEqual(mutant["preservedResults"], inventory(raw["mosaics"]))
        self.assertIn(MUTANT, mutant["reasons"])
        self.assertNotIn("65280", "".join(mutant["preservedResults"]))
        for mosaic in raw["mosaics"]:
            buf = bytes.fromhex(mosaic["packedHex"])
            self.assertNotEqual(
                mutant_plane(buf, mosaic["width"], mosaic["height"]),
                mosaic["codes"],
            )
            self.assertEqual(
                decode_plane(
                    mosaic["format"], buf, mosaic["width"], mosaic["height"], mosaic["rowStride"]
                ),
                mosaic["codes"],
            )

    def test_implementing_the_mutant_would_fail_the_oracle(self) -> None:
        raw = load_document()
        forged = copy.deepcopy(raw)
        for mosaic in forged["mosaics"]:
            mosaic["packedHex"] = b"".join(
                code.to_bytes(2, "little") for row in mosaic["codes"] for code in row
            ).hex()
        with self.assertRaises(ValueError):
            validate_document(forged)
        sensor = raw["mosaics"][0]
        buf = bytearray(bytes.fromhex(sensor["packedHex"]))
        before = bytes(buf)
        decoded = decode_plane("RAW_SENSOR", buf, 4, 4, 12)
        self.assertEqual(bytes(buf), before)
        self.assertEqual(decoded, sensor["codes"])
        self.assertNotEqual(mutant_plane(buf, 4, 4), sensor["codes"])
        self.assertEqual(payload_length("RAW_SENSOR", 4), 8)
        self.assertEqual(payload_length("RAW10", 4), 5)
        self.assertEqual(payload_length("RAW12", 4), 6)
        self.assertFalse(layouts_equivalent("RAW_SENSOR", "RAW10"))
        self.assertFalse(layouts_equivalent("RAW10", "RAW12"))
        self.assertFalse(layouts_equivalent("RAW_SENSOR", "RAW12"))
        self.assertTrue(layouts_equivalent("RAW10", "RAW10"))

    def test_independent_bit_reference_and_untouched_padding(self) -> None:
        raw10 = bytes.fromhex("00ff00ffcc")
        self.assertEqual(decode_row("RAW10", raw10, 4), [0, 1023, 0, 1023])
        self.assertNotEqual(decode_row("RAW_SENSOR", raw10 + b"\x00\x00\x00", 4), [0, 1023, 0, 1023])
        raw12 = bytes.fromhex("00fff000fff0")
        self.assertEqual(decode_row("RAW12", raw12, 4), [0, 4095, 0, 4095])
        self.assertNotEqual(decode_row("RAW10", raw12[:5], 4), [0, 4095, 0, 4095])
        little = pack_plane("RAW_SENSOR", [[1, 0, 1, 0], [0, 1, 0, 1]], 10, b"\x5a\x5a")
        self.assertEqual(little[:8], bytes.fromhex("0100000001000000"))
        self.assertEqual(little[8:10], b"\x5a\x5a")
        self.assertEqual(channel_at("RGGB", 1, 1), "B")
        self.assertEqual(channel_at("BGGR", 1, 1), "R")
        self.assertNotEqual(channel_at("RGGB", 1, 1), channel_at("RGGB", 0, 0))

    def test_corrupt_packed_byte_keeps_the_inventory(self) -> None:
        raw = load_document()
        corrupt = copy.deepcopy(raw)
        hex_text = corrupt["mosaics"][4]["packedHex"]
        corrupt["mosaics"][4]["packedHex"] = "ff" + hex_text[2:]
        result = assess(corrupt)
        self.assert_result(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("decode-mismatch:raw10-rggb", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"], inventory(corrupt["mosaics"]))
        self.assertIn("codes:raw10-rggb:" + RAW10_CODES, result["preservedResults"])
        self.assertIn("id:raw12-bggr", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_invalid_documents_raise(self) -> None:
        valid = load_document()
        extra = copy.deepcopy(valid)
        extra["note"] = "device"
        missing = copy.deepcopy(valid)
        del missing["mutant"]
        wrong_phase = copy.deepcopy(valid)
        wrong_phase["phase"] = "P034"
        wrong_revision = copy.deepcopy(valid)
        wrong_revision["implementationBaseRevision"] = "abc"
        dropped = copy.deepcopy(valid)
        dropped["mosaics"] = dropped["mosaics"][:-1]
        even_crop = copy.deepcopy(valid)
        even_crop["mosaics"][0]["cropLeft"] = 0
        swapped = copy.deepcopy(valid)
        swapped["mosaics"][0]["cfa"] = "BGGR"
        cases = (None, [], {}, extra, missing, wrong_phase, wrong_revision, dropped, even_crop, swapped)
        for sample in cases:
            with self.subTest(sample=type(sample).__name__):
                with self.assertRaises(ValueError):
                    validate_document(sample)


if __name__ == "__main__":
    unittest.main()
