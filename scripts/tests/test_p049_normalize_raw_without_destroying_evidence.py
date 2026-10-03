"""Host checks for the P049 signed RAW normalization kernel. Not a physical S23 probe.

TC-P049-01..08 are specified in separate modules and are not executed here.
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

from p049_normalize_raw_without_destroying_evidence import (  # noqa: E402
    BASE_REVISION,
    CASE_ID,
    FIXTURE,
    MAP_ID,
    METHOD,
    MUTANT,
    ORACLE,
    REFERENCE_VECTORS,
    apply_immediate_clamp,
    assess,
    channel_at,
    check_reference_vectors,
    clamp_unit,
    linear_ratio,
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
SIGNED = (
    ("40", "-3/92"),
    ("64", "0"),
    ("780", "179/184"),
    ("800", "1"),
    ("900", "209/184"),
    ("1023", "959/736"),
)


def load_document() -> dict:
    return json.loads(
        (ROOT / "docs" / "P049_NORMALIZE_RAW_WITHOUT_DESTROYING_EVIDENCE.json").read_text(
            encoding="utf-8"
        )
    )


def independent_ratio(code: str, black: str = "64", white: str = "800") -> str:
    return str(Fraction(int(code) - int(black), int(white) - int(black)))


class P049NormalizeRawTests(unittest.TestCase):
    def assert_result(self, result) -> None:
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], "P049")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))

    def test_constants_encode_method_fixture_oracle_and_mutant(self) -> None:
        self.assertEqual(CASE_ID, "P049")
        self.assertEqual(MAP_ID, "s23-signed-raw-normalization-fixture")
        self.assertEqual(BASE_REVISION, "d4deac8fc82832fd23396a01065c5f0bf9da6670")
        self.assertIn("CFA-aware indexing", METHOD)
        self.assertIn("white exceeds black", METHOD)
        self.assertIn("not a universal scene-white boundary", METHOD)
        self.assertEqual(
            FIXTURE,
            "Codes below black, at black, near white, and beyond an intentionally conservative "
            "white estimate.",
        )
        self.assertEqual(
            ORACLE,
            "The reference retains signed values and reports saturation separately from any "
            "export clipping.",
        )
        self.assertEqual(MUTANT, "Clamp every normalized sample into zero-to-one immediately.")
        check_reference_vectors()

    def test_reference_vectors_match_an_independent_fraction(self) -> None:
        for code, expected in SIGNED:
            self.assertEqual(independent_ratio(code), expected)
            self.assertEqual(linear_ratio(code, "64", "800"), expected)
            self.assertEqual(linear_ratio(code, "64", "800"), independent_ratio(code))
        self.assertEqual(clamp_unit("-3/92"), "0")
        self.assertEqual(clamp_unit("209/184"), "1")
        self.assertEqual(clamp_unit("21/46"), "21/46")
        self.assertNotEqual(linear_ratio("40", "64", "800"), clamp_unit("-3/92"))
        self.assertNotEqual(linear_ratio("900", "64", "800"), "1")
        classes = {item["class"]: item["normalized"] for item in REFERENCE_VECTORS}
        self.assertEqual(classes["below-black"], "-3/92")
        self.assertEqual(classes["beyond-white"], "209/184")
        self.assertNotEqual(classes["below-black"], "0")

    def test_fixture_keeps_signed_units_and_separate_saturation(self) -> None:
        raw = load_document()
        self.assertIsNone(validate_document(raw))
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P049")
        self.assertEqual(raw["mapId"], MAP_ID)
        self.assertEqual(raw["implementationBaseRevision"], BASE_REVISION)
        self.assertEqual(raw["method"], METHOD)
        self.assertEqual(raw["fixture"], FIXTURE)
        self.assertEqual(raw["oracle"], ORACLE)
        self.assertEqual(raw["mutant"], MUTANT)
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "signed_reference")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("below-black:1", result["preservedResults"])
        self.assertIn("at-black:1", result["preservedResults"])
        self.assertIn("near-white:2", result["preservedResults"])
        self.assertIn("at-white:1", result["preservedResults"])
        self.assertIn("beyond-white:2", result["preservedResults"])
        self.assertIn("sensor-saturated:1", result["preservedResults"])
        self.assertIn("export-clip-candidates:3", result["preservedResults"])
        self.assertNotEqual(
            result["preservedResults"].count("sensor-saturated:1"),
            0,
        )
        self.assertIn(
            "s:1,0:code=40:region=active:norm=-3/92:ch=G",
            result["preservedResults"],
        )
        self.assertIn(
            "s:2,0:code=64:region=active:norm=0:ch=R",
            result["preservedResults"],
        )
        self.assertIn(
            "s:4,0:code=800:region=active:norm=1:ch=R",
            result["preservedResults"],
        )
        self.assertIn(
            "s:1,1:code=900:region=active:norm=209/184:ch=B",
            result["preservedResults"],
        )
        self.assertIn(
            "s:2,1:code=1023:region=active:norm=959/736:ch=G",
            result["preservedResults"],
        )
        self.assertIn("vector:below-black:40->-3/92", result["preservedResults"])
        self.assertIn("vector:sensor-saturated:1023->959/736", result["preservedResults"])
        self.assertIn("source-white-is-not-scene-white", result["preservedResults"])
        self.assertIn(ORACLE, result["reasons"])
        self.assertTrue(any("separately from export clipping" in item for item in result["reasons"]))
        self.assertTrue(any("not a universal scene-white boundary" in item for item in result["reasons"]))
        self.assertIn("host fixture is not a physical S23 measurement", result["openQuestions"])
        self.assertEqual(channel_at("RGGB", 1, 0), "G")
        self.assertNotEqual(channel_at("RGGB", 1, 0), channel_at("RGGB", 0, 0))

    def test_mutant_clamp_is_rejected_and_would_fail_if_implemented(self) -> None:
        raw = load_document()
        honest = assess(raw)
        below = next(item for item in honest["preservedResults"] if item.startswith("s:1,0:"))
        over = next(item for item in honest["preservedResults"] if item.startswith("s:1,1:"))
        self.assertIn("norm=-3/92", below)
        self.assertNotIn("norm=0", below)
        self.assertIn("norm=209/184", over)
        self.assertNotIn("norm=1:", over)
        mutant = apply_immediate_clamp(raw)
        self.assert_result(mutant)
        self.assertEqual(mutant["decision"], "rejected")
        self.assertNotIn(mutant["decision"], {"qualified", "allowed", "signed_reference"})
        self.assertIn("immediate-zero-to-one-clamp", mutant["rejectedClaims"])
        self.assertIn(MUTANT, mutant["reasons"])
        kept = next(item for item in mutant["preservedResults"] if item.startswith("s:1,0:"))
        kept_over = next(item for item in mutant["preservedResults"] if item.startswith("s:1,1:"))
        self.assertIn("norm=-3/92", kept)
        self.assertIn("norm=209/184", kept_over)
        self.assertNotEqual(clamp_unit("-3/92"), "-3/92")
        self.assertIn("cfa:RGGB", mutant["preservedResults"])
        self.assertIn("below-black:1", mutant["preservedResults"])

    def test_odd_crop_does_not_reset_cfa_and_policy_is_explicit(self) -> None:
        raw = load_document()
        result = assess(raw)
        self.assertIn("policy:exclude", result["preservedResults"])
        self.assertIn("crop:4x2+1+0", result["preservedResults"])
        diagnostic = copy.deepcopy(raw)
        diagnostic["opticalBlackPolicy"] = "retain-diagnostic"
        counted = assess(diagnostic)
        self.assertEqual(counted["decision"], "signed_reference")
        self.assertIn("policy:retain-diagnostic", counted["preservedResults"])
        self.assertIn("below-black:3", counted["preservedResults"])
        self.assertIn("at-black:2", counted["preservedResults"])
        self.assertNotIn(counted["decision"], {"qualified", "allowed"})

    def test_invalid_document_raises(self) -> None:
        valid = load_document()
        white = copy.deepcopy(valid)
        white["whiteLevel"] = "64"
        low = copy.deepcopy(valid)
        low["whiteLevel"] = "63"
        extra = copy.deepcopy(valid)
        extra["note"] = "device probe"
        phase = copy.deepcopy(valid)
        phase["phase"] = "P048"
        mutant = copy.deepcopy(valid)
        mutant["mutant"] = "Clamp nothing."
        region = copy.deepcopy(valid)
        region["samples"][1]["region"] = "optical-black"
        overlap = copy.deepcopy(valid)
        overlap["crop"] = "5x2+0+0"
        sat = copy.deepcopy(valid)
        sat["sensorSaturation"] = "799"
        clamped = copy.deepcopy(valid)
        clamped["referenceVectors"][0]["normalized"] = "0"
        dropped = copy.deepcopy(valid)
        dropped["samples"] = dropped["samples"][:-1]
        cases = (
            None,
            [],
            {},
            extra,
            phase,
            white,
            low,
            mutant,
            region,
            overlap,
            sat,
            clamped,
            dropped,
        )
        for sample in cases:
            with self.subTest(sample=type(sample).__name__):
                with self.assertRaises(ValueError):
                    validate_document(sample)
        with self.assertRaises(ValueError):
            linear_ratio("10", "64", "64")


if __name__ == "__main__":
    unittest.main()
