"""Host checks for the P051 row-streamed bilinear demosaic. Not a physical S23 probe.

TC-P051-01..08 are specified in separate modules and are not executed here.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from fractions import Fraction
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "gates"))

from p051_build_the_row_streamed_reference_demosaic import (  # noqa: E402
    BASE_REVISION,
    BORDER_POLICY,
    CASE_ID,
    FIXTURE,
    MAP_ID,
    METHOD,
    MUTANT,
    ORACLE,
    ROW_WINDOW,
    WHITE_BALANCE,
    RowWindow,
    apply_white_balance,
    assess,
    channel_at,
    demosaic,
    demosaic_fractions,
    demosaic_mixed_gains,
    demosaic_stale_mutant,
    format_image,
    format_pixel,
    scale_mosaic,
    stream_demosaic,
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


def load_document() -> dict:
    path = ROOT / "docs" / "P051_BUILD_THE_ROW_STREAMED_REFERENCE_DEMOSAIC.json"
    return json.loads(path.read_text(encoding="utf-8"))


def scene(document: dict, ident: str) -> dict:
    return next(item for item in document["scenes"] if item["id"] == ident)


class P051DemosaicTests(unittest.TestCase):
    def assert_result(self, result) -> None:
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], "P051")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))

    def test_constants_encode_method_fixture_oracle_and_mutant(self) -> None:
        self.assertEqual(CASE_ID, "P051")
        self.assertEqual(MAP_ID, "s23-row-streamed-bilinear-demosaic-fixture")
        self.assertEqual(BASE_REVISION, "d4deac8fc82832fd23396a01065c5f0bf9da6670")
        self.assertEqual(
            METHOD,
            "Implement an explicitly documented bilinear reference with deterministic "
            "border treatment and row ownership. Separate white balance placement from "
            "interpolation decisions. Test constant fields, impulses, edges, "
            "checkerboards, and crop boundaries.",
        )
        self.assertEqual(
            FIXTURE,
            "A small Bayer impulse near each edge and a uniform color field with "
            "padded source rows.",
        )
        self.assertEqual(
            ORACLE,
            "The output matches hand-derived border values and never reads outside "
            "retained source rows.",
        )
        self.assertEqual(MUTANT, "Read a missing neighboring row from a stale buffer slot.")
        self.assertIn("omitted from the average", BORDER_POLICY)
        self.assertIn("stale-slot", BORDER_POLICY)
        self.assertIn("does not take white-balance gains", WHITE_BALANCE)
        self.assertIn("Three owned row slots", ROW_WINDOW)

    def test_fixture_matches_hand_derived_borders_and_keeps_padding(self) -> None:
        raw = load_document()
        self.assertIsNone(validate_document(raw))
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P051")
        self.assertEqual(raw["implementationBaseRevision"], BASE_REVISION)
        self.assertEqual(raw["method"], METHOD)
        self.assertEqual(raw["fixture"], FIXTURE)
        self.assertEqual(raw["oracle"], ORACLE)
        self.assertEqual(raw["mutant"], MUTANT)
        uniform = scene(raw, "uniform-padded")
        self.assertEqual(uniform["rowStride"], 6)
        self.assertEqual(uniform["width"], 4)
        self.assertEqual(
            uniform["rows"],
            [
                [4, 6, 4, 6, 999, 999],
                [6, 10, 6, 10, 999, 999],
                [4, 6, 4, 6, 999, 999],
                [6, 10, 6, 10, 999, 999],
            ],
        )
        self.assertTrue(all(pixel == "4,6,10" for row in uniform["golden"] for pixel in row))
        top = scene(raw, "impulse-top")
        self.assertEqual(top["rows"][0], [0, 12, 0, 0])
        self.assertEqual(top["golden"][0][0], "0,6,0")
        self.assertEqual(top["golden"][0][1], "0,12,0")
        self.assertEqual(top["golden"][0][2], "0,4,0")
        bottom = scene(raw, "impulse-bottom")
        self.assertEqual(bottom["rows"][3], [12, 0, 0, 0])
        self.assertEqual(bottom["golden"][3][0], "0,12,0")
        self.assertEqual(bottom["golden"][3][1], "0,4,0")
        self.assertEqual(scene(raw, "impulse-left")["golden"][0][0], "0,6,0")
        self.assertEqual(scene(raw, "impulse-left")["golden"][1][0], "0,12,0")
        self.assertEqual(scene(raw, "impulse-right")["golden"][0][3], "0,12,0")
        self.assertEqual(scene(raw, "impulse-right")["golden"][0][2], "0,4,0")
        edge = scene(raw, "edge-vertical")
        self.assertEqual(edge["golden"][0], ["1,2,3", "5,2,3", "9,6,5", "9,8,7"])
        self.assertEqual(edge["golden"][1], ["1,2,3", "5,7/2,3", "9,8,5", "9,8,7"])
        self.assertEqual(scene(raw, "checker-red")["golden"][0][0], "100,0,0")
        self.assertEqual(scene(raw, "checker-red")["golden"][0][1], "50,0,0")
        self.assertEqual(
            scene(raw, "crop-odd")["golden"],
            [["50,0,0", "50,0,0"], ["50,0,0", "100,0,0"]],
        )
        self.assertEqual(scene(raw, "crop-odd")["cropLeft"], 1)
        self.assertEqual(scene(raw, "crop-odd")["cropTop"], 1)
        self.assertEqual(scene(raw, "signed-uniform")["golden"][0][0], "-2,0,5000")
        self.assertEqual(scene(raw, "stale-contrast")["golden"][3][1], "0,0,0")
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "matched")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("scene:uniform-padded", result["preservedResults"])
        self.assertIn("scene:impulse-top", result["preservedResults"])
        self.assertIn("scene:impulse-bottom", result["preservedResults"])
        self.assertIn("scene:impulse-left", result["preservedResults"])
        self.assertIn("scene:impulse-right", result["preservedResults"])
        self.assertIn("padding:uniform-padded", result["preservedResults"])
        self.assertIn("border:impulse-top:0,0:0,6,0", result["preservedResults"])
        self.assertIn(ORACLE, result["reasons"])
        self.assertIn("physical S23 capture unverified", result["openQuestions"])
        for ident in ("uniform-grbg", "uniform-gbrg", "uniform-bggr"):
            self.assertTrue(all(pixel == "4,6,10" for row in scene(raw, ident)["golden"] for pixel in row))

    def test_reference_output_matches_the_hand_literals(self) -> None:
        raw = load_document()
        top = scene(raw, "impulse-top")
        got = format_image(demosaic(top["rows"], "RGGB", 4, 4))
        self.assertEqual(got[0][0], "0,6,0")
        self.assertEqual(got[0][2], "0,4,0")
        self.assertEqual(got[1][1], "0,3,0")
        bottom = scene(raw, "impulse-bottom")
        got = format_image(demosaic(bottom["rows"], "RGGB", 4, 4))
        self.assertEqual(got[3][1], "0,4,0")
        self.assertEqual(got[2][0], "0,4,0")
        edge = scene(raw, "edge-vertical")
        got = format_image(demosaic(edge["rows"], "RGGB", 4, 4))
        self.assertEqual(got[0], ["1,2,3", "5,2,3", "9,6,5", "9,8,7"])
        self.assertEqual(got[1][1], "5,7/2,3")
        checker = scene(raw, "checker-red")
        full = format_image(demosaic(checker["rows"], "RGGB", 4, 4))
        self.assertEqual(full[0][0], "100,0,0")
        self.assertEqual([row[1:3] for row in full[1:3]], scene(raw, "crop-odd")["golden"])
        signed = [[-2, 0], [0, 5000]]
        self.assertEqual(format_image(demosaic(signed, "RGGB", 2, 2))[0][0], "-2,0,5000")
        self.assertEqual(channel_at(0, 0, "RGGB"), "R")
        self.assertEqual(channel_at(1, 1, "RGGB"), "B")
        self.assertEqual(channel_at(0, 0, "GRBG"), "G")
        self.assertEqual(channel_at(0, 0, "GBRG"), "G")
        self.assertEqual(channel_at(0, 0, "BGGR"), "B")

    def test_mutant_stale_slot_disagrees_with_the_hand_border(self) -> None:
        raw = load_document()
        bottom = scene(raw, "impulse-bottom")
        honest = format_image(demosaic(bottom["rows"], "RGGB", 4, 4))
        mutant = format_image(demosaic_stale_mutant(bottom["rows"], "RGGB", 4, 4, None))
        self.assertEqual(honest[3][1], "0,4,0")
        self.assertEqual(mutant[3][1], "0,3,0")
        self.assertNotEqual(honest, mutant)
        contrast = scene(raw, "stale-contrast")
        honest_c = format_image(demosaic(contrast["rows"], "RGGB", 4, 4))
        mutant_c = format_image(demosaic_stale_mutant(contrast["rows"], "RGGB", 4, 4, None))
        self.assertEqual(honest_c[3][1], "0,0,0")
        self.assertEqual(mutant_c[3][1], "0,9/4,0")
        top = scene(raw, "impulse-top")
        seeded = format_image(
            demosaic_stale_mutant(top["rows"], "RGGB", 4, 4, [100, 100, 100, 100])
        )
        self.assertEqual(format_image(demosaic(top["rows"], "RGGB", 4, 4))[0][0], "0,6,0")
        self.assertEqual(seeded[0][0], "0,112/3,50")
        rejected = assess(raw, read_stale=True)
        self.assert_result(rejected)
        self.assertEqual(rejected["decision"], "rejected")
        self.assertNotIn(rejected["decision"], {"qualified", "allowed", "matched"})
        self.assertIn("stale-buffer-slot", rejected["rejectedClaims"])
        self.assertIn(MUTANT, rejected["reasons"])
        self.assertIn("scene:uniform-padded", rejected["preservedResults"])
        self.assertIn("border:impulse-top:0,0:0,6,0", rejected["preservedResults"])
        self.assertIn("padding:uniform-padded", rejected["preservedResults"])
        self.assertGreater(len(rejected["preservedResults"]), 8)

    def test_stream_never_reads_padding_or_a_stale_slot(self) -> None:
        raw = load_document()
        uniform = scene(raw, "uniform-padded")
        image, reads = stream_demosaic(uniform["rows"], "RGGB", 4, 4)
        self.assertTrue(all(pixel == (Fraction(4), Fraction(6), Fraction(10)) for row in image for pixel in row))
        self.assertTrue(any(tag == "missing" for _, _, tag in reads))
        self.assertFalse(any(tag == "stale" for _, _, tag in reads))
        self.assertTrue(all(0 <= x < 4 for _, x, tag in reads if tag == "owned"))
        altered = copy.deepcopy(uniform["rows"])
        for row in altered:
            row[4] = -7
            row[5] = 123456
        self.assertEqual(
            format_image(demosaic(uniform["rows"], "RGGB", 4, 4)),
            format_image(demosaic(altered, "RGGB", 4, 4)),
        )
        window = RowWindow()
        window.open_frame()
        window.load(uniform["rows"], 0, 4, 4)
        uniform["rows"][0][0] = 50
        self.assertEqual(window.owned(0, 0), 4)
        self.assertEqual(sorted(item for item in window.slot_rows if item is not None), [0, 1])
        window.load(uniform["rows"], 1, 4, 4)
        self.assertEqual(sorted(item for item in window.slot_rows if item is not None), [0, 1, 2])
        self.assertNotIn(3, window.slot_rows)

    def test_white_balance_is_outside_interpolation(self) -> None:
        edge = [
            [1, 2, 9, 8],
            [2, 3, 8, 7],
            [1, 2, 9, 8],
            [2, 3, 8, 7],
        ]
        gains = (Fraction(2), Fraction(1), Fraction(1, 2))
        plain = demosaic(edge, "RGGB", 4, 4)
        self.assertEqual(format_pixel(plain[0][0]), "1,2,3")
        after = apply_white_balance(plain, gains)
        before = demosaic_fractions(scale_mosaic(edge, "RGGB", 4, gains), "RGGB", 4, 4)
        self.assertEqual(before, after)
        self.assertEqual(format_pixel(after[0][0]), "2,2,3/2")
        mixed = demosaic_mixed_gains(edge, "RGGB", 4, 4, gains)
        self.assertNotEqual(mixed, after)
        self.assertNotEqual(format_pixel(mixed[0][0]), "2,2,3/2")

    def test_other_cfa_origins_stay_on_the_constant_field(self) -> None:
        mosaics = {
            "RGGB": [[4, 6, 4, 6], [6, 10, 6, 10], [4, 6, 4, 6], [6, 10, 6, 10]],
            "GRBG": [[6, 4, 6, 4], [10, 6, 10, 6], [6, 4, 6, 4], [10, 6, 10, 6]],
            "GBRG": [[6, 10, 6, 10], [4, 6, 4, 6], [6, 10, 6, 10], [4, 6, 4, 6]],
            "BGGR": [[10, 6, 10, 6], [6, 4, 6, 4], [10, 6, 10, 6], [6, 4, 6, 4]],
        }
        for cfa, rows in mosaics.items():
            image = format_image(demosaic(rows, cfa, 4, 4))
            self.assertTrue(all(pixel == "4,6,10" for row in image for pixel in row), cfa)

    def test_golden_mismatch_keeps_the_other_scenes(self) -> None:
        raw = load_document()
        broken = copy.deepcopy(raw)
        scene(broken, "impulse-top")["golden"][0][0] = "9,9,9"
        result = assess(broken)
        self.assert_result(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("golden-mismatch:impulse-top", result["rejectedClaims"])
        self.assertIn("scene:impulse-top", result["preservedResults"])
        self.assertIn("scene:uniform-padded", result["preservedResults"])
        self.assertIn("scene:edge-vertical", result["preservedResults"])
        self.assertIn("padding:uniform-padded", result["preservedResults"])

    def test_invalid_document_raises(self) -> None:
        raw = load_document()
        cases = []
        broken = copy.deepcopy(raw)
        broken["schemaVersion"] = 2
        cases.append(broken)
        broken = copy.deepcopy(raw)
        broken["phase"] = "P050"
        cases.append(broken)
        broken = copy.deepcopy(raw)
        del broken["mutant"]
        cases.append(broken)
        broken = copy.deepcopy(raw)
        broken["note"] = "device"
        cases.append(broken)
        broken = copy.deepcopy(raw)
        broken["scenes"][0]["cfa"] = "RGBG"
        cases.append(broken)
        broken = copy.deepcopy(raw)
        broken["scenes"] = [item for item in broken["scenes"] if item["kind"] != "crop"]
        cases.append(broken)
        broken = copy.deepcopy(raw)
        broken["scenes"] = [item for item in broken["scenes"] if "top" not in item["id"]]
        cases.append(broken)
        for sample in cases:
            with self.subTest(sample=sample.get("phase")):
                with self.assertRaises(ValueError):
                    validate_document(sample)
        with self.assertRaises(ValueError):
            demosaic([[1]], "RGGB")
        with self.assertRaises(ValueError):
            stream_demosaic([[0, 0], [0, 0]], "RGGB", 2, 2, mutant=False, initial_stale=[1, 1])


if __name__ == "__main__":
    unittest.main()
