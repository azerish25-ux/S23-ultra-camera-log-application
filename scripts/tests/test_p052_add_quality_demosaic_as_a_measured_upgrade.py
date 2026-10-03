"""Host checks for the P052 quality demosaic benchmark. Not a physical S23 probe.

TC-P052-01..08 are specified elsewhere and are not executed by this module.
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

from p052_add_quality_demosaic_as_a_measured_upgrade import (  # noqa: E402
    BASE_REVISION,
    CANDIDATE_ID,
    FIXTURE,
    HOST_LIMIT,
    MAP_ID,
    METHOD,
    MUTANT,
    ORACLE,
    REFERENCE_ID,
    assess,
    edge_contrast_gain,
    selected_identity,
    sharpen_would_accept,
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
DIAGONAL_FALSE = (
    "scene:diagonal:fixture:diagonal-high-contrast:falseColor:"
    "ref=1175/48:cand=1475/64:sharp=1475/64"
)
DIAGONAL_EDGE = (
    "scene:diagonal:fixture:diagonal-high-contrast:edgeContrast:"
    "ref=725/63:cand=325/21:sharp=31525/504"
)
POINT_FALSE = (
    "scene:point-lights:fixture:colored-point-lights:falseColor:ref=15/2:cand=0:sharp=0"
)


def load_document() -> dict:
    path = ROOT / "docs" / "P052_ADD_QUALITY_DEMOSAIC_AS_A_MEASURED_UPGRADE.json"
    return json.loads(path.read_text(encoding="utf-8"))


def checker_scene() -> dict:
    rgb = []
    for y in range(8):
        row = []
        for x in range(8):
            if ((x // 2) + (y // 2)) % 2 == 0:
                row.append([20, 30, 40])
            else:
                row.append([80, 70, 50])
        rgb.append(row)
    return {
        "id": "checker",
        "role": "held-out",
        "kind": "checker-regress",
        "cfa": "RGGB",
        "rgb": rgb,
    }


class P052DemosaicTests(unittest.TestCase):
    def assert_result(self, result) -> None:
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], "P052")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "restored-detail"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) and item for item in result[key]))

    def test_constants_encode_method_fixture_oracle_and_mutant(self) -> None:
        self.assertEqual(MAP_ID, "s23-quality-demosaic-fixture")
        self.assertEqual(BASE_REVISION, "d4deac8fc82832fd23396a01065c5f0bf9da6670")
        self.assertIn("edge-aware candidate", METHOD)
        self.assertIn("false color", METHOD)
        self.assertIn("Retain the simpler reference", METHOD)
        self.assertEqual(
            FIXTURE,
            "Fine repeating fabric, diagonal high-contrast edges, colored point lights, "
            "and a slanted edge chart.",
        )
        self.assertEqual(
            ORACLE,
            "The candidate must improve declared artifacts without unacceptable texture "
            "or color regressions across held-out scenes.",
        )
        self.assertEqual(
            MUTANT,
            "Sharpen the output heavily and report the increased edge contrast as restored detail.",
        )
        self.assertEqual(REFERENCE_ID, "bilinear-reference-v1")
        self.assertEqual(CANDIDATE_ID, "edge-aware-v1")

    def test_fixture_selects_edge_aware_and_retains_bilinear(self) -> None:
        raw = load_document()
        self.assertIsNone(validate_document(raw))
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P052")
        self.assertEqual(raw["mapId"], MAP_ID)
        self.assertEqual(raw["implementationBaseRevision"], BASE_REVISION)
        self.assertEqual(raw["method"], METHOD)
        self.assertEqual(raw["fixture"], FIXTURE)
        self.assertEqual(raw["oracle"], ORACLE)
        self.assertEqual(raw["mutant"], MUTANT)
        self.assertGreater(edge_contrast_gain(raw), 0)
        self.assertTrue(sharpen_would_accept(raw))
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "selected")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(selected_identity(raw), CANDIDATE_ID)
        self.assertIn("reference-retained:bilinear-reference-v1", result["preservedResults"])
        self.assertIn("candidate:edge-aware-v1", result["preservedResults"])
        self.assertIn(DIAGONAL_FALSE, result["preservedResults"])
        self.assertIn(DIAGONAL_EDGE, result["preservedResults"])
        self.assertIn(POINT_FALSE, result["preservedResults"])
        self.assertIn(
            "scene:independent-raw:held-out:independent-raw:falseColor:ref=25/2:cand=75/16:sharp=75/16",
            result["preservedResults"],
        )
        self.assertIn(ORACLE, result["reasons"])
        self.assertIn(HOST_LIMIT, result["reasons"])
        self.assertIn("selection does not use edge contrast", result["reasons"])
        self.assertNotIn(MUTANT, result["reasons"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "restored-detail"})
        self.assertTrue(any("not physical qualification" in item for item in result["openQuestions"]))

    def test_mutant_sharpen_is_rejected_even_though_contrast_rises(self) -> None:
        raw = load_document()
        honest = assess(raw)
        mutant = assess(raw, sole_test="heavy-sharpen")
        self.assert_result(mutant)
        self.assertTrue(sharpen_would_accept(raw))
        self.assertGreater(edge_contrast_gain(raw), Fraction(0))
        self.assertEqual(mutant["decision"], "rejected")
        self.assertNotIn(mutant["decision"], {"qualified", "allowed", "selected", "restored-detail"})
        self.assertEqual(mutant["rejectedClaims"][0], "sharpen-as-restored-detail")
        self.assertIn("diagonal:zippering", mutant["rejectedClaims"])
        self.assertIn("diagonal:colorDelta", mutant["rejectedClaims"])
        self.assertEqual(mutant["preservedResults"], honest["preservedResults"])
        self.assertIn(DIAGONAL_FALSE, mutant["preservedResults"])
        self.assertIn(DIAGONAL_EDGE, mutant["preservedResults"])
        self.assertIn("reference-retained:bilinear-reference-v1", mutant["preservedResults"])
        self.assertIn(MUTANT, mutant["reasons"])
        self.assertIn("heavy sharpen was rejected", mutant["openQuestions"])
        self.assertEqual(selected_identity(raw, sole_test="heavy-sharpen"), REFERENCE_ID)
        self.assertNotIn("sharpen-as-restored-detail", honest["rejectedClaims"])

    def test_texture_or_color_regression_keeps_the_other_scenes(self) -> None:
        raw = load_document()
        raw["scenes"].append(checker_scene())
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("checker:zippering", result["rejectedClaims"])
        self.assertIn("checker:aliasing", result["rejectedClaims"])
        self.assertIn("checker:colorDelta", result["rejectedClaims"])
        self.assertIn(DIAGONAL_FALSE, result["preservedResults"])
        self.assertIn(POINT_FALSE, result["preservedResults"])
        self.assertIn("reference-retained:bilinear-reference-v1", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "selected"})

    def test_shortfall_withholds_without_wiping_improved_scenes(self) -> None:
        raw = load_document()
        points = next(scene for scene in raw["scenes"] if scene["id"] == "point-lights")
        flat = [[[40, 40, 40] for _ in range(8)] for _ in range(8)]
        flat[2][2] = [200, 40, 40]
        points["rgb"] = flat
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertIn("point-lights:falseColor:shortfall", result["rejectedClaims"])
        self.assertIn(DIAGONAL_FALSE, result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "selected"})
        self.assertEqual(selected_identity(raw), REFERENCE_ID)

    def test_invalid_documents_and_sole_test_raise(self) -> None:
        valid = load_document()
        extra = copy.deepcopy(valid)
        extra["note"] = "device probe"
        missing = copy.deepcopy(valid)
        del missing["scenes"]
        bad_phase = copy.deepcopy(valid)
        bad_phase["phase"] = "P051"
        bad_mutant = copy.deepcopy(valid)
        bad_mutant["mutant"] = "Accept the sharper picture."
        empty = copy.deepcopy(valid)
        empty["scenes"] = []
        dropped = copy.deepcopy(valid)
        dropped["scenes"] = [scene for scene in dropped["scenes"] if scene["kind"] != "slanted-edge"]
        cases = (
            None,
            [],
            {},
            extra,
            missing,
            bad_phase,
            bad_mutant,
            empty,
            dropped,
            {**valid, "schemaVersion": 2},
            {**valid, "implementationBaseRevision": "abc"},
            {**valid, "referenceId": "edge-aware-v1"},
            {**valid, "declaredArtifacts": ["edgeContrast"]},
        )
        for sample in cases:
            with self.subTest(sample=type(sample).__name__):
                with self.assertRaises(ValueError):
                    validate_document(sample)
        with self.assertRaises(ValueError):
            assess(valid, sole_test="sharpen")


if __name__ == "__main__":
    unittest.main()
