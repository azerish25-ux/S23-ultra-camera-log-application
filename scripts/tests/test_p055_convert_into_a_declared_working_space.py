"""Host checks for the P055 declared working space. Not a physical S23 probe.

TC-P055-01..08 are specified elsewhere and are not executed by this module.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "gates"))

from p055_convert_into_a_declared_working_space import (  # noqa: E402
    BASE_REVISION,
    BOUNDARY,
    FIXTURE,
    HOST_LIMIT,
    MAP_ID,
    METHOD,
    MUTANT,
    MUTANT_PATH,
    ORACLE,
    ORDER,
    PRECISION,
    UNITS,
    WHITE_POINT,
    assess,
    canonical,
    convert_working,
    display_bitmap,
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
    path = ROOT / "docs" / "P055_CONVERT_INTO_A_DECLARED_WORKING_SPACE.json"
    return json.loads(path.read_text(encoding="utf-8"))


class P055WorkingSpaceTests(unittest.TestCase):
    def assert_result(self, result) -> None:
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], "P055")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) and item for item in result[key]))

    def test_constants_encode_method_fixture_oracle_and_mutant(self) -> None:
        self.assertEqual(MAP_ID, "s23-declared-working-space-fixture")
        self.assertEqual(BASE_REVISION, "d4deac8fc82832fd23396a01065c5f0bf9da6670")
        self.assertIn("high-precision working representation", METHOD)
        self.assertIn("negative and above-one channels", METHOD)
        self.assertIn("singular or nonfinite", METHOD)
        self.assertEqual(
            FIXTURE,
            "A saturated source vector that produces a negative working-space channel "
            "and a highlight above diffuse white.",
        )
        self.assertEqual(
            ORACLE,
            "The conversion preserves both values for subsequent processing instead of "
            "forcing display-gamut clipping.",
        )
        self.assertEqual(
            MUTANT,
            "Insert an eight-bit display bitmap between the camera transform and working image.",
        )
        self.assertEqual(ORDER, ("camera-transform", "exposure-scale", "working-store"))
        self.assertEqual(WHITE_POINT, "D65")
        self.assertEqual(UNITS, "scene-linear")
        self.assertEqual(PRECISION, "float64")
        self.assertEqual(BOUNDARY, "documented-storage")

    def test_fixture_preserves_negative_and_highlight(self) -> None:
        raw = load_document()
        self.assertIsNone(validate_document(raw))
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P055")
        self.assertEqual(raw["mapId"], MAP_ID)
        self.assertEqual(raw["implementationBaseRevision"], BASE_REVISION)
        self.assertEqual(raw["method"], METHOD)
        self.assertEqual(raw["fixture"], FIXTURE)
        self.assertEqual(raw["oracle"], ORACLE)
        self.assertEqual(raw["mutant"], MUTANT)
        self.assertEqual(raw["workingSpace"]["whitePoint"], "D65")
        self.assertEqual(raw["workingSpace"]["units"], "scene-linear")
        self.assertEqual(raw["workingSpace"]["order"], list(ORDER))
        working = convert_working(raw["cameraTransform"], raw["source"]["cameraRgb"], raw["exposureScale"])
        self.assertEqual(tuple(canonical(item) for item in working), ("4", "-1.8", "0.2"))
        bitmap = display_bitmap(working)
        self.assertEqual(tuple(canonical(item) for item in bitmap), ("1", "0", "0.2"))
        self.assertNotEqual(bitmap, working)
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "working_retained")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("source:saturated-highlight:2,0.1,0.1", result["preservedResults"])
        self.assertIn("working:4,-1.8,0.2", result["preservedResults"])
        self.assertIn("stored:4,-1.8,0.2", result["preservedResults"])
        self.assertIn("negative:G:-1.8", result["preservedResults"])
        self.assertIn("highlight:R:4", result["preservedResults"])
        self.assertIn("white-point:D65", result["preservedResults"])
        self.assertIn("units:scene-linear", result["preservedResults"])
        self.assertIn("precision:float64", result["preservedResults"])
        self.assertIn("order:camera-transform>exposure-scale>working-store", result["preservedResults"])
        self.assertIn("scale:2", result["preservedResults"])
        self.assertIn("boundary:-8..16", result["preservedResults"])
        self.assertIn("diffuse-white:1", result["preservedResults"])
        self.assertIn("reference:independent-vector:4,-1.8,0.2", result["preservedResults"])
        self.assertIn("display:not-applied", result["preservedResults"])
        self.assertIn(ORACLE, result["reasons"])
        self.assertIn(HOST_LIMIT, result["reasons"])
        self.assertNotIn(MUTANT, result["reasons"])
        self.assertTrue(any("D65" in item for item in result["openQuestions"]))

    def test_mutant_eight_bit_display_bitmap_is_not_the_working_image(self) -> None:
        raw = load_document()
        honest = assess(raw)
        mutant = assess(raw, path=MUTANT_PATH)
        self.assert_result(mutant)
        self.assertEqual(honest["decision"], "working_retained")
        self.assertIn("working:4,-1.8,0.2", honest["preservedResults"])
        self.assertEqual(mutant["decision"], "rejected")
        self.assertEqual(
            mutant["rejectedClaims"],
            ["eight-bit-display-bitmap", "display-gamut-clip"],
        )
        self.assertNotIn(mutant["decision"], {"qualified", "allowed", "working_retained"})
        self.assertIn("working:4,-1.8,0.2", mutant["preservedResults"])
        self.assertIn("negative:G:-1.8", mutant["preservedResults"])
        self.assertIn("highlight:R:4", mutant["preservedResults"])
        self.assertIn("display:1,0,0.2", mutant["preservedResults"])
        self.assertIn("source:saturated-highlight:2,0.1,0.1", mutant["preservedResults"])
        self.assertIn(MUTANT, mutant["reasons"])
        self.assertIn("eight-bit display bitmap was rejected and was not stored", mutant["openQuestions"])
        self.assertEqual(
            [item for item in honest["preservedResults"] if item.startswith("working:")],
            [item for item in mutant["preservedResults"] if item.startswith("working:")],
        )

    def test_reference_disagreement_keeps_the_computed_vector(self) -> None:
        raw = load_document()
        raw["independentReference"]["workingRgb"] = ["0", "0", "0"]
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("reference-disagreement", result["rejectedClaims"])
        self.assertIn("working:4,-1.8,0.2", result["preservedResults"])
        self.assertIn("reference:independent-vector:0,0,0", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "working_retained"})

    def test_singular_transform_is_rejected_and_keeps_the_source(self) -> None:
        raw = load_document()
        raw["cameraTransform"] = ["0", "0", "0", "0", "0", "0", "0", "0", "0"]
        result = assess(raw)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("singular-transform", result["rejectedClaims"])
        self.assertIn("working:unavailable", result["preservedResults"])
        self.assertIn("source:saturated-highlight:2,0.1,0.1", result["preservedResults"])
        self.assertIn("matrix:0,0,0,0,0,0,0,0,0", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_nonfinite_transform_is_rejected(self) -> None:
        raw = load_document()
        raw["cameraTransform"][0] = "NaN"
        result = assess(raw)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["nonfinite-transform"])
        self.assertIn("source:saturated-highlight:2,0.1,0.1", result["preservedResults"])
        self.assertIn("working:unavailable", result["preservedResults"])
        self.assertTrue(any("matrix[0]" in item for item in result["reasons"]))
        mutant = assess(raw, path=MUTANT_PATH)
        self.assertEqual(mutant["decision"], "rejected")
        self.assertEqual(
            mutant["rejectedClaims"],
            ["nonfinite-transform", "eight-bit-display-bitmap"],
        )

    def test_storage_boundary_is_not_a_display_clamp(self) -> None:
        raw = load_document()
        raw["exposureScale"] = "20"
        raw["independentReference"]["workingRgb"] = ["40", "-18", "2"]
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "bounded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("working:40,-18,2", result["preservedResults"])
        self.assertIn("stored:16,-8,2", result["preservedResults"])
        self.assertIn("negative:G:-18", result["preservedResults"])
        self.assertIn("highlight:R:40,B:2", result["preservedResults"])
        self.assertIn("display:not-applied", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "working_retained"})

    def test_missing_fixture_pair_is_withheld(self) -> None:
        raw = load_document()
        raw["cameraTransform"] = ["1", "0", "0", "0", "1", "0", "0", "0", "1"]
        raw["exposureScale"] = "1"
        raw["source"]["cameraRgb"] = ["0.2", "0.3", "0.4"]
        raw["independentReference"]["workingRgb"] = ["0.2", "0.3", "0.4"]
        result = assess(raw)
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("working:0.2,0.3,0.4", result["preservedResults"])
        self.assertIn("negative:none", result["preservedResults"])
        self.assertIn("highlight:none", result["preservedResults"])

    def test_invalid_documents_raise(self) -> None:
        valid = load_document()
        extra = copy.deepcopy(valid)
        extra["note"] = "device"
        missing = copy.deepcopy(valid)
        del missing["mutant"]
        bad_phase = copy.deepcopy(valid)
        bad_phase["phase"] = "P054"
        bad_order = copy.deepcopy(valid)
        bad_order["workingSpace"]["order"] = ["exposure-scale", "camera-transform", "working-store"]
        bad_white = copy.deepcopy(valid)
        bad_white["workingSpace"]["whitePoint"] = "A"
        zero_scale = copy.deepcopy(valid)
        zero_scale["exposureScale"] = "0"
        short = copy.deepcopy(valid)
        short["cameraTransform"] = ["1", "0", "0"]
        cases = (None, [], {}, extra, missing, bad_phase, bad_order, bad_white, zero_scale, short)
        for sample in cases:
            with self.subTest(sample=type(sample).__name__):
                with self.assertRaises(ValueError):
                    validate_document(sample)
        with self.assertRaises(ValueError):
            assess(valid, path="qualified")


if __name__ == "__main__":
    unittest.main()
