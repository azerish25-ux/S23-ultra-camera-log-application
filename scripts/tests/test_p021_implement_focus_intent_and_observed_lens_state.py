"""Host checks for the P021 dual focus model. Not a physical S23 probe.

TC-P021-01..08 are specified in separate modules and are not executed here.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "gates"))

from p021_implement_focus_intent_and_observed_lens_state import (  # noqa: E402
    BASE_REVISION,
    FIXTURE,
    METHOD,
    MODEL_ID,
    MUTANT,
    ORACLE,
    assess_model,
    project_focus,
    validate_model,
)


RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
FIXTURE_PATH = ROOT / "docs" / "P021_IMPLEMENT_FOCUS_INTENT_AND_OBSERVED_LENS_STATE.json"


def load() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


class P021FocusModelTests(unittest.TestCase):
    def assert_contract(self, result: dict) -> None:
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], "P021")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIsInstance(result["reasons"], list)
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) for item in result[key]))

    def test_fixture_encodes_method_fixture_oracle_and_mutant(self) -> None:
        raw = load()
        self.assertIsNone(validate_model(raw))
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P021")
        self.assertEqual(raw["modelId"], MODEL_ID)
        self.assertEqual(raw["implementationBaseRevision"], BASE_REVISION)
        self.assertEqual(raw["method"], METHOD)
        self.assertEqual(raw["fixture"], FIXTURE)
        self.assertEqual(raw["oracle"], ORACLE)
        self.assertEqual(raw["mutant"], MUTANT)
        self.assertEqual(raw["physical"]["namespace"], "physical.lens")
        self.assertEqual(raw["physical"]["unit"], "metres")
        self.assertEqual(raw["physical"]["subject"], "nearby_foreground")
        self.assertIsNone(raw["physical"]["observedDistance"])
        self.assertIs(raw["physical"]["confirmedByResult"], False)
        self.assertEqual(raw["virtual"]["namespace"], "virtual.development")
        self.assertEqual(raw["virtual"]["unit"], "relative_depth")
        self.assertEqual(raw["virtual"]["subject"], "face")
        self.assertEqual(raw["virtual"]["relativeDepth"], "0.62")
        self.assertIs(raw["virtual"]["claimsMetricDistance"], False)
        self.assertIs(raw["sourceSharpness"]["recordedSharpAtVirtualSubject"], False)
        self.assertIs(raw["sourceSharpness"]["independentOfVirtualPlane"], True)
        self.assertNotEqual(raw["physical"]["namespace"], raw["virtual"]["namespace"])
        self.assertNotEqual(raw["physical"]["unit"], raw["virtual"]["unit"])

    def test_projection_keeps_unknown_metres_apart_from_virtual_face(self) -> None:
        raw = load()
        before = copy.deepcopy(raw)
        projected = project_focus(raw)
        self.assertEqual(raw, before)
        self.assertEqual(projected["physical"]["distance"], "unknown")
        self.assertEqual(projected["physical"]["unit"], "metres")
        self.assertEqual(projected["physical"]["subject"], "nearby_foreground")
        self.assertIs(projected["physical"]["confirmed"], False)
        self.assertEqual(projected["virtual"]["relativeDepth"], "0.62")
        self.assertEqual(projected["virtual"]["subject"], "face")
        self.assertEqual(projected["virtual"]["unit"], "relative_depth")
        self.assertIs(projected["virtual"]["claimsMetricDistance"], False)
        self.assertNotEqual(projected["physical"]["distance"], projected["virtual"]["relativeDepth"])
        self.assertEqual(projected["warning"], ORACLE)
        self.assertIs(projected["sourceSharpAtVirtualSubject"], False)
        self.assertIs(projected["sourceSharpnessIndependent"], True)

    def test_fixture_warns_and_preserves_both_namespaces(self) -> None:
        result = assess_model(load(), mutant=False)
        self.assert_contract(result)
        self.assertEqual(result["decision"], "warned")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn(ORACLE, result["reasons"])
        self.assertIn("physical focus distance is unknown", result["openQuestions"])
        self.assertIn("physical.distance:unknown", result["preservedResults"])
        self.assertIn("physical.unit:metres", result["preservedResults"])
        self.assertIn("physical.subject:nearby_foreground", result["preservedResults"])
        self.assertIn("virtual.subject:face", result["preservedResults"])
        self.assertIn("virtual.relativeDepth:0.62", result["preservedResults"])
        self.assertIn("virtual.unit:relative_depth", result["preservedResults"])
        self.assertNotIn("physical.distance:0.62", result["preservedResults"])
        self.assertNotIn("qualified", result["decision"])

    def test_mutant_overwrite_is_rejected_and_physical_distance_is_preserved(self) -> None:
        raw = load()
        before = copy.deepcopy(raw)
        result = assess_model(raw, mutant=True)
        self.assertEqual(raw, before)
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "warned", "separated"})
        self.assertEqual(result["rejectedClaims"], ["overwrite-physical-focus-distance"])
        self.assertIn(MUTANT, result["reasons"])
        self.assertIn(ORACLE, result["reasons"])
        self.assertIn("physical.distance:unknown", result["preservedResults"])
        self.assertIn("virtual.relativeDepth:0.62", result["preservedResults"])
        self.assertNotIn("physical.distance:0.62", result["preservedResults"])
        self.assertIn("physical.unit:metres", result["preservedResults"])
        self.assertNotIn("physical.unit:relative_depth", result["preservedResults"])
        self.assertIn("physical focus distance is unknown", result["openQuestions"])
        again = project_focus(raw)
        self.assertEqual(again["physical"]["distance"], "unknown")
        self.assertNotEqual(again["physical"]["distance"], again["virtual"]["relativeDepth"])

    def test_confirmed_metres_are_not_replaced_by_the_virtual_target(self) -> None:
        raw = load()
        raw["physical"]["confirmedByResult"] = True
        raw["physical"]["observedDistance"] = "0.35"
        honest = assess_model(raw, mutant=False)
        self.assertEqual(honest["decision"], "warned")
        self.assertIn("physical.distance:0.35", honest["preservedResults"])
        self.assertNotIn("physical.distance:unknown", honest["preservedResults"])
        self.assertNotIn("physical.distance:0.62", honest["preservedResults"])
        self.assertEqual(honest["openQuestions"], [])
        self.assertIn(ORACLE, honest["reasons"])
        mutated = assess_model(raw, mutant=True)
        self.assertEqual(mutated["decision"], "rejected")
        self.assertIn("physical.distance:0.35", mutated["preservedResults"])
        self.assertIn("virtual.relativeDepth:0.62", mutated["preservedResults"])
        self.assertNotIn("physical.distance:0.62", mutated["preservedResults"])
        self.assertEqual(raw["physical"]["observedDistance"], "0.35")
        self.assertEqual(raw["physical"]["unit"], "metres")

    def test_equal_numeric_strings_do_not_collapse_units(self) -> None:
        raw = load()
        raw["physical"]["confirmedByResult"] = True
        raw["physical"]["observedDistance"] = "0.62"
        result = assess_model(raw, mutant=True)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("physical.distance:0.62", result["preservedResults"])
        self.assertIn("physical.unit:metres", result["preservedResults"])
        self.assertIn("virtual.unit:relative_depth", result["preservedResults"])
        self.assertIn("virtual.relativeDepth:0.62", result["preservedResults"])
        self.assertNotIn("physical.unit:relative_depth", result["preservedResults"])
        self.assertNotEqual(
            result["preservedResults"].index("physical.unit:metres"),
            result["preservedResults"].index("virtual.unit:relative_depth"),
        )

    def test_sharp_virtual_subject_is_separated_without_the_warning(self) -> None:
        raw = load()
        raw["physical"]["confirmedByResult"] = True
        raw["physical"]["observedDistance"] = "0.35"
        raw["sourceSharpness"]["recordedSharpAtVirtualSubject"] = True
        projected = project_focus(raw)
        self.assertIsNone(projected["warning"])
        result = assess_model(raw, mutant=False)
        self.assertEqual(result["decision"], "separated")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "warned"})
        self.assertNotIn(ORACLE, result["reasons"])
        self.assertIn("source.sharpAtVirtualSubject:true", result["preservedResults"])
        self.assertIn("physical.distance:0.35", result["preservedResults"])
        self.assertEqual(result["openQuestions"], [])
        self.assertEqual(result["rejectedClaims"], [])

    def test_metric_claim_and_coupled_sharpness_are_rejected_without_data_loss(self) -> None:
        metric = load()
        metric["virtual"]["claimsMetricDistance"] = True
        metric_result = assess_model(metric, mutant=False)
        self.assertEqual(metric_result["decision"], "rejected")
        self.assertIn("virtual-metric-distance", metric_result["rejectedClaims"])
        self.assertIn("physical.distance:unknown", metric_result["preservedResults"])
        self.assertIn("virtual.relativeDepth:0.62", metric_result["preservedResults"])
        self.assertNotIn(metric_result["decision"], {"qualified", "allowed"})

        coupled = load()
        coupled["sourceSharpness"]["independentOfVirtualPlane"] = False
        coupled_result = assess_model(coupled, mutant=False)
        self.assertEqual(coupled_result["decision"], "rejected")
        self.assertIn("source-sharpness-coupled-to-virtual-plane", coupled_result["rejectedClaims"])
        self.assertIn("virtual.subject:face", coupled_result["preservedResults"])
        self.assertIn("physical.subject:nearby_foreground", coupled_result["preservedResults"])

    def test_invalid_models_raise(self) -> None:
        valid = load()
        confirmed = copy.deepcopy(valid)
        confirmed["physical"]["confirmedByResult"] = True
        confirmed["physical"]["observedDistance"] = "0.35"
        self.assertIsNone(validate_model(confirmed))
        guessed = copy.deepcopy(valid)
        guessed["physical"]["observedDistance"] = "0.35"
        merged_unit = copy.deepcopy(valid)
        merged_unit["physical"]["unit"] = "relative_depth"
        merged_namespace = copy.deepcopy(valid)
        merged_namespace["virtual"]["namespace"] = "physical.lens"
        metric_depth = copy.deepcopy(valid)
        metric_depth["virtual"]["relativeDepth"] = "1.5"
        zero_depth = copy.deepcopy(valid)
        zero_depth["virtual"]["relativeDepth"] = "0"
        bool_depth = copy.deepcopy(valid)
        bool_depth["virtual"]["relativeDepth"] = True
        extra = copy.deepcopy(valid)
        extra["qualified"] = True
        missing = copy.deepcopy(valid)
        del missing["oracle"]
        wrong_phase = copy.deepcopy(valid)
        wrong_phase["phase"] = "P020"
        wrong_revision = copy.deepcopy(valid)
        wrong_revision["implementationBaseRevision"] = "fffd5c9a63cb732e103052acae29ae0c251585cc"
        unconfirmed_number = copy.deepcopy(valid)
        unconfirmed_number["physical"]["confirmedByResult"] = True
        unconfirmed_number["physical"]["observedDistance"] = None
        cases = (
            None,
            [],
            {},
            guessed,
            merged_unit,
            merged_namespace,
            metric_depth,
            zero_depth,
            bool_depth,
            extra,
            missing,
            wrong_phase,
            wrong_revision,
            unconfirmed_number,
        )
        for sample in cases:
            with self.subTest(sample=type(sample).__name__):
                with self.assertRaises(ValueError):
                    validate_model(sample)
        with self.assertRaises(ValueError):
            assess_model(valid, mutant="true")
        with self.assertRaises(ValueError):
            assess_model(valid, mutant=1)


if __name__ == "__main__":
    unittest.main()
