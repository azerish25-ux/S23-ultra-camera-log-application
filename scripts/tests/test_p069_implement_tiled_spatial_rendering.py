"""Host checks for the P069 tiled spatial renderer. Not a physical S23 probe.

TC-P069-01..08 are specified elsewhere and are not executed by this module.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "gates"))

from p069_implement_tiled_spatial_rendering import (  # noqa: E402
    BASE_REVISION,
    FIXTURE,
    HOST_LIMIT,
    MAP_ID,
    METHOD,
    MUTANT,
    MUTANT_PATH,
    ORACLE,
    assess,
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
    path = ROOT / "docs" / "P069_IMPLEMENT_TILED_SPATIAL_RENDERING.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _node(document: dict, effect: str) -> dict:
    return next(item for item in document["nodes"] if item["effect"] == effect)


class P069TiledSpatialRenderingTests(unittest.TestCase):
    def assert_result(self, result) -> None:
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], "P069")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) and item for item in result[key]))

    def test_constants_encode_method_fixture_oracle_and_mutant(self) -> None:
        self.assertEqual(MAP_ID, "s23-tiled-spatial-rendering-fixture")
        self.assertEqual(BASE_REVISION, "d4deac8fc82832fd23396a01065c5f0bf9da6670")
        self.assertIn("maximum kernel support", METHOD)
        self.assertIn("crop only after dependencies finish", METHOD)
        self.assertIn("global coordinates for grain and lens", METHOD)
        self.assertIn("boundaries and corners", METHOD)
        self.assertEqual(
            FIXTURE,
            "A bright impulse centered exactly on a tile boundary with halation, blur, "
            "and deterministic grain enabled.",
        )
        self.assertEqual(
            ORACLE,
            "The assembled result matches the declared untiled tolerance and contains no seam "
            "or repeated grain block.",
        )
        self.assertEqual(MUTANT, "Apply every effect independently inside tiles without overlap.")

    def test_fixture_matches_untiled_reference_at_the_boundary_corner(self) -> None:
        raw = load_document()
        self.assertIsNone(validate_document(raw))
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P069")
        self.assertEqual(raw["mapId"], MAP_ID)
        self.assertEqual(raw["implementationBaseRevision"], BASE_REVISION)
        self.assertEqual(raw["method"], METHOD)
        self.assertEqual(raw["fixture"], FIXTURE)
        self.assertEqual(raw["oracle"], ORACLE)
        self.assertEqual(raw["mutant"], MUTANT)
        self.assertEqual(raw["impulse"], {"x": 4, "y": 4, "value": "1"})
        self.assertEqual(raw["planner"]["tileSize"], 4)
        self.assertIs(raw["planner"]["cropAfterDependencies"], True)
        self.assertIs(raw["planner"]["globalCoordinates"], True)
        self.assertEqual(_node(raw, "blur")["kernelSupport"], "1")
        self.assertEqual(_node(raw, "halation")["kernelSupport"], "1")
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "assembled_match")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "rejected", "withheld"})
        self.assertIn(ORACLE, result["reasons"])
        self.assertIn(HOST_LIMIT, result["reasons"])
        self.assertNotIn(MUTANT, result["reasons"])
        preserved = result["preservedResults"]
        self.assertIn("impulse:4,4:value=1", preserved)
        self.assertIn("node:blur:halo=1:kernel=1:kind=spatial", preserved)
        self.assertIn("node:halation:halo=1:kernel=1:kind=spatial", preserved)
        self.assertIn("node:lens:halo=0:kernel=0:kind=coordinate", preserved)
        self.assertIn("node:grain:halo=0:kernel=0:kind=coordinate", preserved)
        self.assertIn("max-kernel-support:1", preserved)
        self.assertIn("required-overlap:2", preserved)
        self.assertIn("applied-overlap:2", preserved)
        self.assertIn("boundary:true", preserved)
        self.assertIn("corner:true", preserved)
        self.assertIn("max-delta:0", preserved)
        self.assertIn("seam:false", preserved)
        self.assertIn("repeated-grain:false", preserved)
        self.assertIn("reference:untiled", preserved)
        for line in preserved:
            if line.startswith("sample:"):
                tiled, untiled = line.split(":tiled=")[1].split(":untiled=")
                self.assertEqual(tiled, untiled)

    def test_mutant_independent_tiles_without_overlap_are_rejected(self) -> None:
        raw = load_document()
        result = assess(raw, MUTANT_PATH)
        self.assert_result(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "assembled_match"})
        self.assertEqual(
            result["rejectedClaims"],
            [
                "seam",
                "tolerance-exceeded",
                "repeated-grain-block",
                "missing-overlap",
                "local-coordinates",
                "independent-tiles-without-overlap",
            ],
        )
        self.assertIn(MUTANT, result["reasons"])
        preserved = result["preservedResults"]
        self.assertIn("impulse:4,4:value=1", preserved)
        self.assertIn("node:blur:halo=1:kernel=1:kind=spatial", preserved)
        self.assertIn("node:grain:halo=0:kernel=0:kind=coordinate", preserved)
        self.assertIn("applied-overlap:0", preserved)
        self.assertIn("applied-independent:true", preserved)
        self.assertIn("seam:true", preserved)
        self.assertIn("repeated-grain:true", preserved)
        self.assertNotIn("max-delta:0", preserved)
        self.assertTrue(any(item.startswith("sample:4,4:tiled=") for item in preserved))
        mismatched = [
            item
            for item in preserved
            if item.startswith("sample:") and item.split(":tiled=")[1].split(":untiled=")[0]
            != item.split(":untiled=")[1]
        ]
        self.assertTrue(mismatched)

    def test_repeat_corner_and_non_corner_boundary(self) -> None:
        corner = load_document()
        corner["impulse"] = {"x": 4, "y": 4, "value": "1"}
        edge = load_document()
        edge["impulse"] = {"x": 4, "y": 1, "value": "1"}
        corner_result = assess(corner)
        edge_result = assess(edge)
        self.assertEqual(corner_result["decision"], "assembled_match")
        self.assertIn("corner:true", corner_result["preservedResults"])
        self.assertEqual(edge_result["decision"], "assembled_match")
        self.assertIn("boundary:true", edge_result["preservedResults"])
        self.assertIn("corner:false", edge_result["preservedResults"])
        self.assertIn("max-delta:0", edge_result["preservedResults"])
        self.assertIn("impulse:4,1:value=1", edge_result["preservedResults"])

    def test_repeat_varied_tile_size_and_maximum_blur(self) -> None:
        small = load_document()
        small["planner"]["tileSize"] = 2
        small["impulse"] = {"x": 2, "y": 6, "value": "1"}
        wide = load_document()
        wide["planner"]["width"] = 16
        wide["planner"]["height"] = 16
        wide["planner"]["tileSize"] = 8
        wide["impulse"] = {"x": 8, "y": 8, "value": "1"}
        _node(wide, "blur")["kernelSupport"] = "3"
        _node(wide, "halation")["kernelSupport"] = "2"
        small_result = assess(small)
        wide_result = assess(wide)
        self.assertEqual(small_result["decision"], "assembled_match")
        self.assertIn("tile-size:2", small_result["preservedResults"])
        self.assertIn("corner:true", small_result["preservedResults"])
        self.assertEqual(wide_result["decision"], "assembled_match")
        self.assertIn("node:blur:halo=3:kernel=3:kind=spatial", wide_result["preservedResults"])
        self.assertIn("max-kernel-support:3", wide_result["preservedResults"])
        self.assertIn("required-overlap:5", wide_result["preservedResults"])
        self.assertIn("applied-overlap:5", wide_result["preservedResults"])
        self.assertIn("max-delta:0", wide_result["preservedResults"])
        self.assertIn("seam:false", wide_result["preservedResults"])

    def test_early_crop_and_local_coordinates_are_rejected_without_wiping_nodes(self) -> None:
        early = load_document()
        early["planner"]["cropAfterDependencies"] = False
        local = load_document()
        local["planner"]["globalCoordinates"] = False
        early_result = assess(early)
        local_result = assess(local)
        self.assertEqual(early_result["decision"], "rejected")
        self.assertIn("cropped-before-dependencies", early_result["rejectedClaims"])
        self.assertIn("missing-overlap", early_result["rejectedClaims"])
        self.assertIn("seam", early_result["rejectedClaims"])
        self.assertNotIn("independent-tiles-without-overlap", early_result["rejectedClaims"])
        self.assertIn("node:halation:halo=1:kernel=1:kind=spatial", early_result["preservedResults"])
        self.assertEqual(local_result["decision"], "rejected")
        self.assertIn("local-coordinates", local_result["rejectedClaims"])
        self.assertIn("repeated-grain-block", local_result["rejectedClaims"])
        self.assertIn("global-coordinates:false", local_result["preservedResults"])
        self.assertIn("impulse:4,4:value=1", local_result["preservedResults"])
        self.assertNotIn(local_result["decision"], {"qualified", "allowed", "assembled_match"})

    def test_interior_impulse_or_missing_effect_is_withheld(self) -> None:
        interior = load_document()
        interior["impulse"] = {"x": 1, "y": 1, "value": "1"}
        dropped = load_document()
        dropped["nodes"] = [node for node in dropped["nodes"] if node["effect"] != "grain"]
        interior_result = assess(interior)
        dropped_result = assess(dropped)
        self.assertEqual(interior_result["decision"], "withheld")
        self.assertEqual(interior_result["rejectedClaims"], [])
        self.assertIn("boundary:false", interior_result["preservedResults"])
        self.assertIn("max-delta:0", interior_result["preservedResults"])
        self.assertIn("impulse:1,1:value=1", interior_result["preservedResults"])
        self.assertEqual(dropped_result["decision"], "withheld")
        self.assertIn("effects:blur,halation,lens", dropped_result["preservedResults"])
        self.assertNotIn(dropped_result["decision"], {"qualified", "allowed", "assembled_match"})

    def test_mutant_on_a_matching_document_does_not_become_assembled_match(self) -> None:
        raw = load_document()
        declared = assess(raw)
        mutant = assess(raw, MUTANT_PATH)
        self.assertEqual(declared["decision"], "assembled_match")
        self.assertEqual(mutant["decision"], "rejected")
        self.assertIn("impulse:4,4:value=1", mutant["preservedResults"])
        self.assertGreater(
            len(mutant["preservedResults"]),
            8,
        )

    def test_invalid_documents_and_paths_raise(self) -> None:
        valid = load_document()
        extra = copy.deepcopy(valid)
        extra["note"] = "device probe"
        missing = copy.deepcopy(valid)
        del missing["mutant"]
        bad_phase = copy.deepcopy(valid)
        bad_phase["phase"] = "P068"
        bad_revision = copy.deepcopy(valid)
        bad_revision["implementationBaseRevision"] = "abc"
        undivided = copy.deepcopy(valid)
        undivided["planner"]["tileSize"] = 3
        bool_width = copy.deepcopy(valid)
        bool_width["planner"]["width"] = True
        loose = copy.deepcopy(valid)
        loose["planner"]["tolerance"] = "0.0"
        zero_blur = copy.deepcopy(valid)
        _node(zero_blur, "blur")["kernelSupport"] = "0"
        lens_halo = copy.deepcopy(valid)
        _node(lens_halo, "lens")["kernelSupport"] = "1"
        swapped = copy.deepcopy(valid)
        swapped["nodes"][0], swapped["nodes"][1] = swapped["nodes"][1], swapped["nodes"][0]
        outside = copy.deepcopy(valid)
        outside["impulse"]["x"] = 8
        duplicate = copy.deepcopy(valid)
        duplicate["nodes"].append(copy.deepcopy(duplicate["nodes"][0]))
        cases = (
            None,
            [],
            {},
            extra,
            missing,
            bad_phase,
            bad_revision,
            undivided,
            bool_width,
            loose,
            zero_blur,
            lens_halo,
            swapped,
            outside,
            duplicate,
        )
        for sample in cases:
            with self.subTest(sample=type(sample).__name__):
                with self.assertRaises(ValueError):
                    validate_document(sample)
        with self.assertRaises(ValueError):
            assess(valid, "untyped-handles")
        untouched = load_document()
        assess(valid, MUTANT_PATH)
        self.assertEqual(valid, untouched)


if __name__ == "__main__":
    unittest.main()
