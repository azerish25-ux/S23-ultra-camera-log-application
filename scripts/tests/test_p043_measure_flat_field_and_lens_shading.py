"""Host checks for the P043 flat-field shading fixture. Not a physical S23 probe.

TC-P043-01..08 are specified in separate modules and are not executed here.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "gates"))

from p043_measure_flat_field_and_lens_shading import (  # noqa: E402
    BASE_REVISION,
    CASE_ID,
    FIXTURE,
    MAP_ID,
    METHOD,
    MUTANT,
    MUTANT_APPLICATION,
    ORACLE,
    assess,
    authored_gains,
    preserved_inventory,
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
INVENTORY = [
    "lens:s23-wide",
    "focus:infinity",
    "aperture:f1.8",
    "exposureNs:10000000",
    "firmware:host-fixture-1",
    "cfa:RGGB",
    "source:4000x3000",
    "captureCrop:3998x2998+1+0",
    "mapCrop:3998x2998+0+0",
    "mapCfa:RGGB",
    "mapFrame:sensor-crop",
    "mapOrientation:native",
    "field:0.8,0.9,1.1,1.2",
    "gains:1.04,1.01,1.01,1.04",
    "gainBounds:0.5..2",
    "validation:holdout-flat:1,1,1,1",
]


def load_document() -> dict:
    return json.loads(
        (ROOT / "docs" / "P043_MEASURE_FLAT_FIELD_AND_LENS_SHADING.json").read_text(encoding="utf-8")
    )


def aligned(raw: dict | None = None) -> dict:
    document = copy.deepcopy(raw or load_document())
    document["capture"]["crop"] = "4000x3000+0+0"
    document["shadingMap"]["crop"] = "4000x3000+0+0"
    document["shadingMap"]["frame"] = "sensor-crop"
    document["shadingMap"]["orientation"] = "native"
    document["shadingMap"]["appliedAfterRotation"] = False
    document["field"]["kind"] = "uniform"
    document["field"]["samples"] = ["1", "1", "1", "1"]
    document["shadingMap"]["gains"] = ["1.04", "1.01", "1.01", "1.04"]
    document["validation"]["separate"] = True
    document["validation"]["samples"] = ["1", "1", "1", "1"]
    return document


class P043FlatFieldTests(unittest.TestCase):
    def assert_result(self, result: dict) -> None:
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], "P043")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))

    def test_constants_encode_method_fixture_oracle_and_mutant(self) -> None:
        self.assertEqual(CASE_ID, "P043")
        self.assertEqual(MAP_ID, "s23-flat-field-shading-fixture")
        self.assertEqual(BASE_REVISION, "d4deac8fc82832fd23396a01065c5f0bf9da6670")
        self.assertIn("diffuse uniform fields", METHOD)
        self.assertIn("reject gradients caused by the light source", METHOD)
        self.assertIn("actual crop and CFA", METHOD)
        self.assertIn("bound correction gains", METHOD)
        self.assertIn("separate flat capture", METHOD)
        self.assertEqual(
            FIXTURE,
            "A flat field with a deliberate illumination gradient and a mismatched crop origin.",
        )
        self.assertEqual(
            ORACLE,
            "The pipeline does not absorb the lighting gradient into a supposedly universal "
            "lens-shading correction and detects coordinate mismatch.",
        )
        self.assertEqual(MUTANT, "Apply a shading map in display coordinates after rotation.")

    def test_fixture_rejects_gradient_and_crop_mismatch_without_absorbing_it(self) -> None:
        raw = load_document()
        before = copy.deepcopy(raw)
        self.assertIsNone(validate_document(raw))
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P043")
        self.assertEqual(raw["mapId"], MAP_ID)
        self.assertEqual(raw["implementationBaseRevision"], BASE_REVISION)
        self.assertEqual(raw["method"], METHOD)
        self.assertEqual(raw["fixture"], FIXTURE)
        self.assertEqual(raw["oracle"], ORACLE)
        self.assertEqual(raw["mutant"], MUTANT)
        self.assertEqual(authored_gains(raw), ["1.04", "1.01", "1.01", "1.04"])
        products = [
            Decimal(field) * Decimal(gain)
            for field, gain in zip(raw["field"]["samples"], raw["shadingMap"]["gains"])
        ]
        self.assertGreater(max(products) - min(products), Decimal("0.2"))
        result = assess(raw)
        self.assertEqual(raw, before)
        self.assert_result(result)
        self.assertEqual(result["decision"], "shading_rejected")
        self.assertEqual(
            result["rejectedClaims"],
            ["illumination-gradient", "crop-origin-mismatch", "odd-crop-origin"],
        )
        self.assertNotIn("gradient-absorbed", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"], INVENTORY)
        self.assertEqual(result["preservedResults"], preserved_inventory(raw))
        self.assertIn(ORACLE, result["reasons"])
        self.assertIn(
            "lighting gradient was not absorbed into the lens-shading correction",
            result["reasons"],
        )
        self.assertIn(
            "coordinate mismatch: capture crop 3998x2998+1+0 versus map crop 3998x2998+0+0",
            result["reasons"],
        )
        self.assertIn("odd crop origin 1+0 is not aligned to the shading map", result["reasons"])
        self.assertTrue(any("does not qualify a physical S23" in item for item in result["reasons"]))
        self.assertNotIn(MUTANT, result["reasons"])
        self.assertIn("physical S23 flat-field unverified", result["openQuestions"])

    def test_mutant_display_after_rotation_is_rejected_on_an_aligned_field(self) -> None:
        raw = aligned()
        sensor = assess(raw)
        mutant = assess(raw, application=MUTANT_APPLICATION)
        self.assertEqual(sensor["decision"], "host_consistent")
        self.assert_result(mutant)
        self.assertEqual(mutant["decision"], "rejected")
        self.assertNotIn(mutant["decision"], {"qualified", "allowed", "host_consistent", "shading_rejected"})
        self.assertNotEqual(mutant["decision"], sensor["decision"])
        self.assertEqual(mutant["rejectedClaims"], ["display-after-rotation"])
        self.assertEqual(mutant["preservedResults"], sensor["preservedResults"])
        self.assertIn("gains:1.04,1.01,1.01,1.04", mutant["preservedResults"])
        self.assertIn("field:1,1,1,1", mutant["preservedResults"])
        self.assertNotIn("gains:1.04,1.04,1.01,1.01", mutant["preservedResults"])
        self.assertIn(MUTANT, mutant["reasons"])
        self.assertIn("shading gains were not reprojected into display space", mutant["reasons"])
        self.assertIn("display-space shading was not applied", mutant["openQuestions"])

    def test_mutant_on_the_fixture_keeps_the_gradient_inventory(self) -> None:
        raw = load_document()
        sensor = assess(raw)
        mutant = assess(raw, application="display-after-rotation")
        self.assertEqual(mutant["decision"], "rejected")
        self.assertEqual(mutant["rejectedClaims"][0], "display-after-rotation")
        self.assertIn("illumination-gradient", mutant["rejectedClaims"])
        self.assertIn("crop-origin-mismatch", mutant["rejectedClaims"])
        self.assertEqual(mutant["preservedResults"], sensor["preservedResults"])
        self.assertIn("field:0.8,0.9,1.1,1.2", mutant["preservedResults"])
        self.assertIn(MUTANT, mutant["reasons"])
        self.assertIn(
            "lighting gradient was not absorbed into the lens-shading correction",
            mutant["reasons"],
        )

    def test_absorbing_the_gradient_is_rejected_and_samples_stay(self) -> None:
        raw = load_document()
        raw["shadingMap"]["gains"] = ["1.25", "1.1", "0.9", "0.8"]
        result = assess(raw)
        self.assertEqual(result["decision"], "shading_rejected")
        self.assertIn("gradient-absorbed", result["rejectedClaims"])
        self.assertIn("illumination-gradient", result["rejectedClaims"])
        self.assertIn("field:0.8,0.9,1.1,1.2", result["preservedResults"])
        self.assertIn("gains:1.25,1.1,0.9,0.8", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "host_consistent"})
        self.assertIn(
            "monotonic shading gains track the lighting gradient and were refused",
            result["reasons"],
        )

    def test_uniform_aligned_field_is_only_host_consistent(self) -> None:
        result = assess(aligned())
        self.assert_result(result)
        self.assertEqual(result["decision"], "host_consistent")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("field:1,1,1,1", result["preservedResults"])
        self.assertIn("captureCrop:4000x3000+0+0", result["preservedResults"])
        self.assertIn("mapCrop:4000x3000+0+0", result["preservedResults"])
        self.assertIn("validation:holdout-flat:1,1,1,1", result["preservedResults"])
        self.assertIn("uniform illumination was not converted into a shading ramp", result["reasons"])
        self.assertIn("coordinates match the capture crop and CFA", result["reasons"])
        self.assertIn("physical S23 flat-field unverified", result["openQuestions"])

    def test_non_uniform_holdout_is_withheld(self) -> None:
        raw = aligned()
        raw["validation"]["samples"] = ["1", "1.1", "1", "0.9"]
        result = assess(raw)
        self.assertEqual(result["decision"], "withheld")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "host_consistent"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("validation:holdout-flat:1,1.1,1,0.9", result["preservedResults"])
        self.assertIn("field:1,1,1,1", result["preservedResults"])
        self.assertIn("holdout flat is not uniform", result["openQuestions"])
        self.assertIn("correction is not certified", result["reasons"])

    def test_unbounded_gain_and_same_capture_validation_keep_the_field(self) -> None:
        unbounded = load_document()
        unbounded["shadingMap"]["gains"] = ["2.1", "1.01", "1.01", "1.04"]
        high = assess(unbounded)
        self.assertIn("gain-unbounded", high["rejectedClaims"])
        self.assertIn("field:0.8,0.9,1.1,1.2", high["preservedResults"])
        self.assertIn("gains:2.1,1.01,1.01,1.04", high["preservedResults"])
        reused = load_document()
        reused["validation"]["separate"] = False
        shared = assess(reused)
        self.assertEqual(shared["decision"], "shading_rejected")
        self.assertIn("validation-not-separate", shared["rejectedClaims"])
        self.assertIn("validation:holdout-flat:1,1,1,1", shared["preservedResults"])
        self.assertIn("captureCrop:3998x2998+1+0", shared["preservedResults"])

    def test_invalid_documents_and_applications_raise(self) -> None:
        valid = load_document()
        extra = copy.deepcopy(valid)
        extra["note"] = "device"
        missing = copy.deepcopy(valid)
        del missing["mutant"]
        bad_gain = copy.deepcopy(valid)
        bad_gain["shadingMap"]["gains"] = ["1.00", "1.01", "1.01", "1.04"]
        bad_crop = copy.deepcopy(valid)
        bad_crop["capture"]["crop"] = "3998X2998+1+0"
        short = copy.deepcopy(valid)
        short["field"]["samples"] = ["0.8", "0.9", "1.1"]
        short["shadingMap"]["gains"] = ["1.04", "1.01", "1.04"]
        short["validation"]["samples"] = ["1", "1", "1"]
        inverted = copy.deepcopy(valid)
        inverted["gainBounds"] = {"min": "2", "max": "0.5"}
        cases = (
            None,
            [],
            {},
            extra,
            missing,
            bad_gain,
            bad_crop,
            short,
            inverted,
            {**valid, "schemaVersion": True},
            {**valid, "phase": "P042"},
            {**valid, "mapId": "other"},
            {**valid, "implementationBaseRevision": "abc"},
            {**valid, "method": "probe the phone"},
        )
        for sample in cases:
            with self.subTest(sample=type(sample).__name__):
                with self.assertRaises(ValueError):
                    validate_document(sample)
        with self.assertRaises(ValueError):
            assess(valid, application="display")
        with self.assertRaises(ValueError):
            assess(valid, application="allowed")


if __name__ == "__main__":
    unittest.main()
