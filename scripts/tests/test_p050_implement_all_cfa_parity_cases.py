"""Host checks for the P050 CFA parity fixture. Not a physical S23 probe.

TC-P050-01..08 are specified in separate modules and are not executed here.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "gates"))

from p050_implement_all_cfa_parity_cases import (  # noqa: E402
    BASE_REVISION,
    CASE_ID,
    FIXTURE,
    MAP_ID,
    METHOD,
    MUTANT,
    ORACLE,
    apply_origin_reset,
    assess,
    carried_channel,
    channel_at,
    demosaic,
    green_checkerboard,
    inventory,
    red_blue_swap,
    reset_origin_channel,
    rotate_developed,
    synthetic_plane,
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
CODES = {"R": 17, "G": 400, "B": 901}
# Independent 2x2 rows. Not derived by calling channel_at.
HAND = {
    ("RGGB", 1, 1): ("BG", "GR"),
    ("BGGR", 1, 1): ("RG", "GB"),
    ("GRBG", 1, 1): ("GB", "RG"),
    ("GBRG", 1, 1): ("GR", "BG"),
    ("RGGB", 1, 0): ("GR", "BG"),
}


def load_document() -> dict:
    return json.loads(
        (ROOT / "docs" / "P050_IMPLEMENT_ALL_CFA_PARITY_CASES.json").read_text(
            encoding="utf-8"
        )
    )


class P050CfaParityTests(unittest.TestCase):
    def assert_result(self, result) -> None:
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], "P050")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))

    def test_constants_encode_method_fixture_oracle_and_mutant(self) -> None:
        self.assertEqual(CASE_ID, "P050")
        self.assertEqual(MAP_ID, "s23-cfa-parity-fixture")
        self.assertEqual(BASE_REVISION, "d4deac8fc82832fd23396a01065c5f0bf9da6670")
        self.assertIn("original CFA origin", METHOD)
        self.assertIn("RGGB", METHOD)
        self.assertIn("GBRG", METHOD)
        self.assertIn("Rotate developed RGB only after", METHOD)
        self.assertEqual(
            FIXTURE,
            "An odd-offset crop of each CFA with red, green, and blue codes deliberately "
            "far apart.",
        )
        self.assertEqual(
            ORACLE,
            "The resulting channel identity matches the independent fixture without "
            "red-blue swaps or green checkerboards.",
        )
        self.assertEqual(
            MUTANT,
            "Reset CFA origin to the top-left of every cropped buffer.",
        )

    def test_hand_table_matches_carried_origin_not_buffer_origin(self) -> None:
        for (cfa, left, top), rows in HAND.items():
            for y, row in enumerate(rows):
                for x, expected in enumerate(row):
                    self.assertEqual(channel_at(cfa, left + x, top + y), expected)
                    self.assertEqual(carried_channel(cfa, left, top, x, y), expected)
        self.assertEqual(carried_channel("RGGB", 1, 1, 0, 0), "B")
        self.assertEqual(reset_origin_channel("RGGB", 0, 0), "R")
        self.assertNotEqual(
            carried_channel("RGGB", 1, 1, 0, 0),
            reset_origin_channel("RGGB", 0, 0),
        )

    def test_fixture_matches_each_cfa_without_swap_or_checkerboard(self) -> None:
        raw = load_document()
        self.assertIsNone(validate_document(raw))
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P050")
        self.assertEqual(raw["implementationBaseRevision"], BASE_REVISION)
        self.assertEqual(raw["method"], METHOD)
        self.assertEqual(raw["fixture"], FIXTURE)
        self.assertEqual(raw["oracle"], ORACLE)
        self.assertEqual(raw["mutant"], MUTANT)
        self.assertEqual({item["cfa"] for item in raw["planes"]}, {"RGGB", "BGGR", "GRBG", "GBRG"})
        for plane in raw["planes"]:
            key = (plane["cfa"], plane["cropLeft"], plane["cropTop"])
            self.assertEqual(tuple("".join(row) for row in plane["expectedChannels"]), HAND[key])
            self.assertTrue(plane["cropLeft"] % 2 == 1 or plane["cropTop"] % 2 == 1)
            self.assertFalse(
                red_blue_swap(
                    plane["cfa"],
                    plane["cropLeft"],
                    plane["cropTop"],
                    plane["samples"],
                    CODES,
                    False,
                )
            )
            self.assertFalse(
                green_checkerboard(
                    plane["cfa"], plane["cropLeft"], plane["cropTop"], plane["samples"], False
                )
            )
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "matched")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"], inventory(raw))
        self.assertIn("rggb-odd:RGGB@1,1:BG/GR", result["preservedResults"])
        self.assertIn("bggr-odd:BGGR@1,1:RG/GB", result["preservedResults"])
        self.assertIn("grbg-odd:GRBG@1,1:GB/RG", result["preservedResults"])
        self.assertIn("gbrg-odd:GBRG@1,1:GR/BG", result["preservedResults"])
        self.assertIn("rggb-odd-left:RGGB@1,0:GR/BG", result["preservedResults"])
        self.assertIn("pad:rggb-odd:2:7", result["preservedResults"])
        self.assertIn("codes:R17,G400,B901", result["preservedResults"])
        self.assertIn(ORACLE, result["reasons"])
        self.assertIn("no red-blue swap", result["reasons"])
        self.assertIn("no green checkerboard", result["reasons"])
        self.assertIn("physical S23 CFA unverified", result["openQuestions"])

    def test_demosaic_uses_carried_constants_then_rotation(self) -> None:
        for (cfa, left, top), _rows in HAND.items():
            plane = synthetic_plane(cfa, 2, 2, left, top, CODES)
            image = demosaic(cfa, left, top, plane)
            self.assertEqual(image[0][0], (17, 400, 901))
            rotated = rotate_developed(image, 90)
            self.assertEqual(rotated[0][0], (17, 400, 901))
            self.assertEqual(len(rotated), 2)
            self.assertEqual(len(rotated[0]), 2)
        gradient = [[(1, 0, 0), (2, 0, 0)], [(3, 0, 0), (4, 0, 0)]]
        self.assertEqual(
            rotate_developed(gradient, 90),
            [[(3, 0, 0), (1, 0, 0)], [(4, 0, 0), (2, 0, 0)]],
        )
        odd = synthetic_plane("RGGB", 2, 2, 1, 1, CODES)
        swapped = demosaic("RGGB", 0, 0, odd)
        self.assertEqual(swapped[0][0], (901, 400, 17))
        self.assertNotEqual(swapped[0][0], (17, 400, 901))
        mixed = synthetic_plane("RGGB", 2, 2, 1, 0, CODES)
        with self.assertRaises(ValueError):
            demosaic("RGGB", 0, 0, mixed)
        self.assertEqual(demosaic("RGGB", 1, 0, mixed)[0][0], (17, 400, 901))

    def test_mutant_origin_reset_is_rejected_and_inventory_remains(self) -> None:
        raw = load_document()
        mutant = apply_origin_reset(raw)
        self.assert_result(mutant)
        self.assertEqual(mutant["decision"], "rejected")
        self.assertNotIn(mutant["decision"], {"qualified", "allowed", "matched"})
        self.assertIn("cfa-origin-reset", mutant["rejectedClaims"])
        self.assertIn(MUTANT, mutant["reasons"])
        self.assertIn("red-blue swap:rggb-odd", mutant["reasons"])
        self.assertIn("red-blue-swap:rggb-odd", mutant["rejectedClaims"])
        self.assertIn("green checkerboard:rggb-odd-left", mutant["reasons"])
        self.assertIn("green-checkerboard:rggb-odd-left", mutant["rejectedClaims"])
        for token in inventory(raw):
            self.assertIn(token, mutant["preservedResults"])
        self.assertIn("reset:rggb-odd:RG/GB", mutant["preservedResults"])
        self.assertNotIn("matched", [mutant["decision"]])
        carried = [item for item in mutant["preservedResults"] if item.startswith("rggb-odd:")]
        self.assertEqual(carried, ["rggb-odd:RGGB@1,1:BG/GR"])

    def test_invalid_document_raises(self) -> None:
        raw = load_document()
        cases = []
        broken = copy.deepcopy(raw)
        broken["schemaVersion"] = 2
        cases.append(broken)
        broken = copy.deepcopy(raw)
        broken["phase"] = "P049"
        cases.append(broken)
        broken = copy.deepcopy(raw)
        del broken["mutant"]
        cases.append(broken)
        broken = copy.deepcopy(raw)
        broken["extra"] = True
        cases.append(broken)
        broken = copy.deepcopy(raw)
        broken["planes"][0]["cfa"] = "XXXX"
        cases.append(broken)
        broken = copy.deepcopy(raw)
        broken["planes"][0]["rotationOrder"] = "mosaic-first"
        cases.append(broken)
        broken = copy.deepcopy(raw)
        broken["planes"][0]["samples"][0][0] = 7
        cases.append(broken)
        broken = copy.deepcopy(raw)
        broken["codes"]["R"] = 400
        cases.append(broken)
        for item in cases:
            with self.subTest(phase=item.get("phase"), keys=sorted(item)):
                with self.assertRaises(ValueError):
                    validate_document(item)


if __name__ == "__main__":
    unittest.main()
