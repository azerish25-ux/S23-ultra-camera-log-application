"""Host checks for the P054 optional denoise stage. Not a physical S23 probe.

TC-P054-01..08 are specified elsewhere and are not executed by this module.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "gates"))

from p054_implement_denoising_as_an_optional_processing_st import (  # noqa: E402
    BASE_REVISION,
    FIXTURE,
    HOST_LIMIT,
    MAP_ID,
    METHOD,
    MUTANT,
    MUTANT_ACCEPT,
    MUTANT_METHOD,
    ORACLE,
    assess,
    frame_average_is_quieter,
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
    path = ROOT / "docs" / "P054_IMPLEMENT_DENOISING_AS_AN_OPTIONAL_PROCESSING_ST.json"
    return json.loads(path.read_text(encoding="utf-8"))


class P054DenoiseTests(unittest.TestCase):
    def assert_result(self, result) -> None:
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], "P054")
        self.assertNotIn(result["decision"], {"qualified", "allowed", MUTANT_ACCEPT})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) and item for item in result[key]))

    def test_constants_encode_method_fixture_oracle_and_mutant(self) -> None:
        self.assertEqual(MAP_ID, "s23-optional-denoise-fixture")
        self.assertEqual(BASE_REVISION, "d4deac8fc82832fd23396a01065c5f0bf9da6670")
        self.assertIn("conservative spatial reference", METHOD)
        self.assertIn("motion confidence", METHOD)
        self.assertIn("artistic grain", METHOD)
        self.assertIn("algorithm version", METHOD)
        self.assertEqual(
            FIXTURE,
            "Low-light hair, moving fabric, a static wall, and a slowly moving colored point light.",
        )
        self.assertEqual(
            ORACLE,
            "Noise reduction cannot pass by smearing all texture or leaving motion trails "
            "beyond the declared quality gate.",
        )
        self.assertEqual(MUTANT, "Use frame averaging without motion or occlusion handling.")

    def test_fixture_keeps_spatial_reference_inside_the_gate(self) -> None:
        raw = load_document()
        self.assertIsNone(validate_document(raw))
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P054")
        self.assertEqual(raw["mapId"], MAP_ID)
        self.assertEqual(raw["implementationBaseRevision"], BASE_REVISION)
        self.assertEqual(raw["method"], METHOD)
        self.assertEqual(raw["fixture"], FIXTURE)
        self.assertEqual(raw["oracle"], ORACLE)
        self.assertEqual(raw["mutant"], MUTANT)
        self.assertTrue(frame_average_is_quieter(raw))
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "optional-stage")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn(
            "scene:low-light-hair:texture=0.92:trail=0:noise-before=0.08:noise-after=0.05:"
            "residual=0.03:confidence=1:occlusion=no",
            result["preservedResults"],
        )
        self.assertIn(
            "scene:moving-fabric:texture=0.9:trail=0.01:noise-before=0.04:noise-after=0.03:"
            "residual=0.01:confidence=0.35:occlusion=no",
            result["preservedResults"],
        )
        self.assertIn(
            "scene:static-wall:texture=0.97:trail=0:noise-before=0.03:noise-after=0.012:"
            "residual=0.018:confidence=1:occlusion=no",
            result["preservedResults"],
        )
        self.assertIn(
            "scene:point-light:texture=0.94:trail=0.012:noise-before=0.02:noise-after=0.015:"
            "residual=0.005:confidence=0.62:occlusion=no",
            result["preservedResults"],
        )
        self.assertIn(
            "frame-average:moving-fabric:texture=0.4:trail=0.22:noise=0.008",
            result["preservedResults"],
        )
        self.assertIn("strength:0.25", result["preservedResults"])
        self.assertIn("algorithm:spatial-ref-1", result["preservedResults"])
        self.assertIn("spatial:conservative-box-3", result["preservedResults"])
        self.assertIn("noise-char:sensor-read-noise", result["preservedResults"])
        self.assertIn("grain:not-applied", result["preservedResults"])
        self.assertIn("stage:on", result["preservedResults"])
        self.assertIn("residuals:inspectable", result["preservedResults"])
        self.assertIn("clean-source:untouched", result["preservedResults"])
        self.assertIn("gate:trail<=0.02:texture>=0.85", result["preservedResults"])
        self.assertIn(ORACLE, result["reasons"])
        self.assertIn(HOST_LIMIT, result["reasons"])
        self.assertIn(
            "moving-fabric texture 0.9 trail 0.01 noise 0.03 is inside the quality gate",
            result["reasons"],
        )
        self.assertIn(
            "temporal candidate moving-fabric motion confidence 0.35 is below 0.5",
            result["openQuestions"],
        )
        self.assertNotIn(MUTANT, result["reasons"])
        self.assertNotIn(MUTANT_ACCEPT, result["reasons"])

    def test_mutant_frame_average_is_rejected_even_when_quieter(self) -> None:
        raw = load_document()
        honest = assess(raw)
        mutant = assess(raw, processing=MUTANT_METHOD)
        self.assert_result(mutant)
        self.assertTrue(frame_average_is_quieter(raw))
        self.assertEqual(mutant["decision"], "rejected")
        self.assertNotIn(mutant["decision"], {"qualified", "allowed", "optional-stage", MUTANT_ACCEPT})
        self.assertEqual(
            mutant["rejectedClaims"],
            [
                "frame-average-without-motion",
                "motion-confidence-ignored",
                "texture-smear:low-light-hair",
                "motion-trail:low-light-hair",
                "texture-smear:moving-fabric",
                "motion-trail:moving-fabric",
                "texture-smear:point-light",
                "motion-trail:point-light",
            ],
        )
        self.assertEqual(mutant["preservedResults"], honest["preservedResults"])
        self.assertIn(
            "frame-average:point-light:texture=0.5:trail=0.18:noise=0.004",
            mutant["preservedResults"],
        )
        self.assertIn("scene:static-wall:texture=0.97:trail=0:noise-before=0.03:noise-after=0.012:residual=0.018:confidence=1:occlusion=no", mutant["preservedResults"])
        self.assertIn(MUTANT, mutant["reasons"])
        self.assertIn("frame averaging without motion or occlusion handling was rejected", mutant["openQuestions"])
        self.assertNotIn("frame-average-without-motion", honest["rejectedClaims"])
        self.assertIn(
            "moving-fabric texture 0.4 trail 0.22 noise 0.008 is outside the quality gate",
            mutant["reasons"],
        )

    def test_mutant_is_rejected_even_when_metrics_are_inside_the_gate(self) -> None:
        raw = load_document()
        for scene in raw["scenes"]:
            scene["frameAverageTexture"] = scene["textureRetention"]
            scene["frameAverageTrail"] = scene["motionTrail"]
            scene["frameAverageNoise"] = "0.001"
        self.assertTrue(frame_average_is_quieter(raw))
        mutant = assess(raw, processing=MUTANT_METHOD)
        self.assertEqual(mutant["decision"], "rejected")
        self.assertEqual(
            mutant["rejectedClaims"],
            ["frame-average-without-motion", "motion-confidence-ignored"],
        )
        self.assertNotIn(mutant["decision"], {"qualified", "allowed", "optional-stage", MUTANT_ACCEPT})
        self.assertIn("frame-average:low-light-hair:texture=0.92:trail=0:noise=0.001", mutant["preservedResults"])
        self.assertIn(MUTANT, mutant["reasons"])

    def test_occlusion_ignored_by_frame_average_stays_rejected(self) -> None:
        raw = load_document()
        raw["scenes"][1]["occlusion"] = True
        mutant = assess(raw, processing=MUTANT_METHOD)
        honest = assess(raw)
        self.assertIn("occlusion-ignored", mutant["rejectedClaims"])
        self.assertEqual(mutant["decision"], "rejected")
        self.assertNotIn(mutant["decision"], {"qualified", "allowed", MUTANT_ACCEPT})
        self.assertIn("occlusion on moving-fabric limits temporal history", mutant["openQuestions"])
        self.assertEqual(honest["decision"], "optional-stage")
        self.assertNotIn("occlusion-ignored", honest["rejectedClaims"])
        self.assertIn(
            "scene:moving-fabric:texture=0.9:trail=0.01:noise-before=0.04:noise-after=0.03:"
            "residual=0.01:confidence=0.35:occlusion=yes",
            mutant["preservedResults"],
        )

    def test_texture_smear_and_motion_trail_reject_without_wiping_inventory(self) -> None:
        raw = load_document()
        raw["scenes"][0]["textureRetention"] = "0.2"
        smeared = assess(raw)
        self.assertEqual(smeared["decision"], "rejected")
        self.assertIn("texture-smear:low-light-hair", smeared["rejectedClaims"])
        self.assertIn(
            "scene:low-light-hair:texture=0.2:trail=0:noise-before=0.08:noise-after=0.05:"
            "residual=0.03:confidence=1:occlusion=no",
            smeared["preservedResults"],
        )
        self.assertTrue(any(item.startswith("frame-average:point-light:") for item in smeared["preservedResults"]))
        trailed = load_document()
        trailed["scenes"][1]["motionTrail"] = "0.2"
        result = assess(trailed)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("motion-trail:moving-fabric", result["rejectedClaims"])
        self.assertIn("strength:0.25", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "optional-stage"})

    def test_disable_stage_contamination_grain_and_hidden_residuals(self) -> None:
        disabled = load_document()
        disabled["stageEnabled"] = False
        off = assess(disabled)
        self.assertEqual(off["decision"], "disabled")
        self.assertEqual(off["rejectedClaims"], [])
        self.assertIn("stage:off", off["preservedResults"])
        self.assertIn("stage is disabled and was not applied to clean source", off["openQuestions"])
        self.assertNotIn(off["decision"], {"qualified", "allowed", "optional-stage"})
        dirty = load_document()
        dirty["cleanSourceUntouched"] = False
        contaminated = assess(dirty)
        self.assertEqual(contaminated["decision"], "rejected")
        self.assertIn("clean-source-contaminated", contaminated["rejectedClaims"])
        self.assertIn("clean-source:contaminated", contaminated["preservedResults"])
        grain = load_document()
        grain["artisticGrain"] = "sensor-read-noise"
        mixed = assess(grain)
        self.assertEqual(mixed["decision"], "rejected")
        self.assertIn("noise-grain-conflated", mixed["rejectedClaims"])
        self.assertIn("artistic-grain-applied", mixed["rejectedClaims"])
        hidden = load_document()
        hidden["residualInspectable"] = False
        withheld = assess(hidden)
        self.assertEqual(withheld["decision"], "rejected")
        self.assertIn("residuals-not-inspectable", withheld["rejectedClaims"])
        self.assertIn("residuals:hidden", withheld["preservedResults"])
        steep = load_document()
        steep["strength"] = "0.9"
        aggressive = assess(steep)
        self.assertEqual(aggressive["decision"], "rejected")
        self.assertIn("aggressive-strength", aggressive["rejectedClaims"])
        self.assertIn("strength:0.9", aggressive["preservedResults"])

    def test_residual_mismatch_keeps_declared_numbers(self) -> None:
        raw = load_document()
        raw["scenes"][2]["residual"] = "0.001"
        result = assess(raw)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("residual-mismatch:static-wall", result["rejectedClaims"])
        self.assertIn(
            "scene:static-wall:texture=0.97:trail=0:noise-before=0.03:noise-after=0.012:"
            "residual=0.001:confidence=1:occlusion=no",
            result["preservedResults"],
        )

    def test_invalid_documents_and_processing_raise(self) -> None:
        valid = load_document()
        extra = copy.deepcopy(valid)
        extra["note"] = "device probe"
        missing = copy.deepcopy(valid)
        del missing["scenes"]
        bad_phase = copy.deepcopy(valid)
        bad_phase["phase"] = "P053"
        bad_mutant = copy.deepcopy(valid)
        bad_mutant["mutant"] = "Average every frame."
        short = copy.deepcopy(valid)
        short["scenes"] = short["scenes"][:3]
        bad_strength = copy.deepcopy(valid)
        bad_strength["strength"] = "0.250"
        cases = (
            None,
            [],
            {},
            extra,
            missing,
            bad_phase,
            bad_mutant,
            short,
            bad_strength,
            {**valid, "schemaVersion": 2},
            {**valid, "implementationBaseRevision": "abc"},
            {**valid, "stageEnabled": 1},
            {**valid, "spatialReference": ""},
        )
        for sample in cases:
            with self.subTest(sample=type(sample).__name__):
                with self.assertRaises(ValueError):
                    validate_document(sample)
        with self.assertRaises(ValueError):
            assess(valid, processing="frame-average")
        with self.assertRaises(ValueError):
            frame_average_is_quieter({"phase": "P054"})


if __name__ == "__main__":
    unittest.main()
