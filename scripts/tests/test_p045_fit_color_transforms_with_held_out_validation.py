"""Host checks for the P045 held-out color fit. Not a physical S23 probe.

TC-P045-01..08 are specified elsewhere and are not executed by this module.
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

from p045_fit_color_transforms_with_held_out_validation import (  # noqa: E402
    BASE_REVISION,
    FIXTURE,
    HELD_OUT_FAIL,
    HOST_LIMIT,
    MAP_ID,
    METHOD,
    MUTANT,
    MUTANT_ACCEPT,
    ORACLE,
    TRAIN_LIMIT,
    assess,
    canonical,
    frobenius_condition,
    held_out_error,
    training_only_would_accept,
    training_rmse,
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
    path = ROOT / "docs" / "P045_FIT_COLOR_TRANSFORMS_WITH_HELD_OUT_VALIDATION.json"
    return json.loads(path.read_text(encoding="utf-8"))


class P045ColorFitTests(unittest.TestCase):
    def assert_result(self, result) -> None:
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], "P045")
        self.assertNotIn(result["decision"], {"qualified", "allowed", MUTANT_ACCEPT})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) and item for item in result[key]))

    def test_constants_encode_method_fixture_oracle_and_mutant(self) -> None:
        self.assertEqual(MAP_ID, "s23-held-out-color-fit-fixture")
        self.assertEqual(BASE_REVISION, "d4deac8fc82832fd23396a01065c5f0bf9da6670")
        self.assertIn("linearized source measurements", METHOD)
        self.assertIn("held-out patches", METHOD)
        self.assertIn("neutral preservation", METHOD)
        self.assertEqual(
            FIXTURE,
            "A chart fit with low training error but large held-out saturated-blue error "
            "under a second light source.",
        )
        self.assertEqual(
            ORACLE,
            "The profile remains limited to its validated conditions and the report exposes "
            "the held-out failure.",
        )
        self.assertEqual(MUTANT, "Validate a fit only against the same patches used to estimate it.")
        self.assertEqual(TRAIN_LIMIT, Decimal("0.02"))
        self.assertEqual(HELD_OUT_FAIL, Decimal("0.15"))

    def test_fixture_exposes_held_out_failure_and_limits_the_profile(self) -> None:
        raw = load_document()
        self.assertIsNone(validate_document(raw))
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P045")
        self.assertEqual(raw["mapId"], MAP_ID)
        self.assertEqual(raw["implementationBaseRevision"], BASE_REVISION)
        self.assertEqual(raw["method"], METHOD)
        self.assertEqual(raw["fixture"], FIXTURE)
        self.assertEqual(raw["oracle"], ORACLE)
        self.assertEqual(raw["mutant"], MUTANT)
        self.assertEqual(training_rmse(raw), Decimal(0))
        self.assertEqual(held_out_error(raw, "saturated-blue"), Decimal("0.5"))
        self.assertEqual(frobenius_condition(raw["matrix"]), Decimal(3))
        self.assertTrue(training_only_would_accept(raw))
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "limited")
        self.assertEqual(
            result["rejectedClaims"],
            ["held-out-saturated-blue", "second-illuminant"],
        )
        self.assertIn("training:N18:w=4:e=0", result["preservedResults"])
        self.assertIn("training:red:w=1:e=0", result["preservedResults"])
        self.assertIn("held-out:saturated-blue:A:e=0.5", result["preservedResults"])
        self.assertIn("training-rmse:0", result["preservedResults"])
        self.assertIn("conditioning:3", result["preservedResults"])
        self.assertIn("neutral:N18:preserved", result["preservedResults"])
        self.assertIn("scene:scene-skin:D65:skin", result["preservedResults"])
        self.assertIn("scene:scene-fabric:D65:saturated-fabric", result["preservedResults"])
        self.assertIn("scene:scene-foliage:D65:foliage", result["preservedResults"])
        self.assertIn("scene:scene-narrow:narrow-band:narrow-band", result["preservedResults"])
        self.assertIn("weighting:inverse-variance", result["preservedResults"])
        self.assertIn("fit-illuminant:D65", result["preservedResults"])
        self.assertIn(ORACLE, result["reasons"])
        self.assertIn("held-out saturated-blue error 0.5 under A", result["reasons"])
        self.assertIn(HOST_LIMIT, result["reasons"])
        self.assertTrue(any("second light A is not supported" in item for item in result["openQuestions"]))
        self.assertNotIn(MUTANT, result["reasons"])
        self.assertNotIn("training_validated", result["reasons"])

    def test_mutant_training_only_validation_is_rejected(self) -> None:
        raw = load_document()
        honest = assess(raw)
        mutant = assess(raw, sole_test="training-patches-only")
        self.assert_result(mutant)
        self.assertTrue(training_only_would_accept(raw))
        self.assertLessEqual(training_rmse(raw), TRAIN_LIMIT)
        self.assertGreaterEqual(held_out_error(raw, "saturated-blue"), HELD_OUT_FAIL)
        self.assertEqual(mutant["decision"], "rejected")
        self.assertNotIn(mutant["decision"], {"qualified", "allowed", "limited", MUTANT_ACCEPT})
        self.assertEqual(
            mutant["rejectedClaims"],
            ["training-only-validation", "held-out-saturated-blue", "second-illuminant"],
        )
        self.assertEqual(mutant["preservedResults"], honest["preservedResults"])
        self.assertIn("held-out:saturated-blue:A:e=0.5", mutant["preservedResults"])
        self.assertIn("training-rmse:0", mutant["preservedResults"])
        self.assertIn(MUTANT, mutant["reasons"])
        self.assertIn("training-only validation was rejected", mutant["openQuestions"])
        self.assertNotIn("training-only-validation", honest["rejectedClaims"])

    def test_mutant_still_rejects_when_held_out_error_is_zero(self) -> None:
        raw = load_document()
        raw["heldOut"][0]["target"] = list(raw["heldOut"][0]["source"])
        self.assertEqual(held_out_error(raw, "saturated-blue"), Decimal(0))
        self.assertTrue(training_only_would_accept(raw))
        honest = assess(raw)
        mutant = assess(raw, sole_test="training-patches-only")
        self.assertEqual(honest["decision"], "withheld")
        self.assertNotIn("held-out-saturated-blue", honest["rejectedClaims"])
        self.assertEqual(mutant["decision"], "rejected")
        self.assertEqual(mutant["rejectedClaims"], ["training-only-validation"])
        self.assertIn("held-out:saturated-blue:A:e=0", mutant["preservedResults"])
        self.assertNotIn(mutant["decision"], {"qualified", "allowed", MUTANT_ACCEPT, "limited"})

    def test_training_error_does_not_erase_held_out_inventory(self) -> None:
        raw = load_document()
        raw["training"][1]["target"] = ["0.1", "0.1", "0.1"]
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("training-error", result["rejectedClaims"])
        self.assertIn("held-out-saturated-blue", result["rejectedClaims"])
        self.assertIn("held-out:saturated-blue:A:e=0.5", result["preservedResults"])
        self.assertTrue(result["preservedResults"][1].startswith("training:red:"))
        self.assertNotIn(result["decision"], {"qualified", "allowed", "limited"})

    def test_singular_and_ill_conditioned_matrices_are_rejected(self) -> None:
        singular = load_document()
        singular["matrix"] = ["1", "0", "0", "0", "1", "0", "0", "0", "0"]
        self.assertFalse(training_only_would_accept(singular))
        rejected = assess(singular)
        self.assertEqual(rejected["decision"], "rejected")
        self.assertIn("singular-matrix", rejected["rejectedClaims"])
        self.assertIn("held-out:saturated-blue:A:e=unavailable", rejected["preservedResults"])
        self.assertIn("conditioning:singular", rejected["preservedResults"])
        steep = load_document()
        steep["matrix"] = ["1", "0", "0", "0", "1", "0", "0", "0", "0.0001"]
        self.assertGreaterEqual(frobenius_condition(steep["matrix"]), Decimal("1000"))
        ill = assess(steep)
        self.assertEqual(ill["decision"], "rejected")
        self.assertIn("ill-conditioned", ill["rejectedClaims"])
        self.assertNotIn(ill["decision"], {"qualified", "allowed", "limited"})
        self.assertTrue(any(item.startswith("held-out:saturated-blue:") for item in ill["preservedResults"]))
        self.assertIn("conditioning:" + canonical(frobenius_condition(steep["matrix"])), ill["preservedResults"])

    def test_neutral_shift_is_not_silently_preserved(self) -> None:
        raw = load_document()
        raw["training"][0]["target"] = ["0.2", "0.18", "0.18"]
        result = assess(raw)
        self.assertEqual(result["decision"], "limited")
        self.assertIn("neutral-shift", result["rejectedClaims"])
        self.assertIn("neutral:N18:shifted", result["preservedResults"])
        self.assertIn("held-out:saturated-blue:A:e=0.5", result["preservedResults"])
        raw["heldOut"][0]["target"] = list(raw["heldOut"][0]["source"])
        shifted_only = assess(raw)
        self.assertEqual(shifted_only["decision"], "rejected")
        self.assertIn("neutral-shift", shifted_only["rejectedClaims"])
        self.assertNotIn(shifted_only["decision"], {"qualified", "allowed"})

    def test_invalid_documents_and_sole_test_raise(self) -> None:
        valid = load_document()
        extra = copy.deepcopy(valid)
        extra["note"] = "device probe"
        missing = copy.deepcopy(valid)
        del missing["heldOut"]
        bad_phase = copy.deepcopy(valid)
        bad_phase["phase"] = "P044"
        bad_mutant = copy.deepcopy(valid)
        bad_mutant["mutant"] = "Accept the training patches."
        empty = copy.deepcopy(valid)
        empty["training"] = []
        scenes = copy.deepcopy(valid)
        scenes["naturalScenes"] = []
        cases = (
            None,
            [],
            {},
            extra,
            missing,
            bad_phase,
            bad_mutant,
            empty,
            scenes,
            {**valid, "schemaVersion": 2},
            {**valid, "implementationBaseRevision": "abc"},
            {**valid, "weighting": "uniform"},
            {**valid, "matrix": ["1", "0", "0"]},
        )
        for sample in cases:
            with self.subTest(sample=type(sample).__name__):
                with self.assertRaises(ValueError):
                    validate_document(sample)
        with self.assertRaises(ValueError):
            assess(valid, sole_test="training-patches")
        with self.assertRaises(ValueError):
            held_out_error(valid, "missing-patch")


if __name__ == "__main__":
    unittest.main()
