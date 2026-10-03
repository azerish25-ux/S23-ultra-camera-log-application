"""Host checks for P062 display and Log export branches. Not a physical S23 probe.

TC-P062-01..08 are specified elsewhere and are not executed by this module.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "gates"))

from p062_implement_display_and_log_export_branches import (  # noqa: E402
    BASE_REVISION,
    CLEAN_NAME,
    ENCODING,
    EXCLUDED,
    FIXTURE,
    HOST_LIMIT,
    MAP_ID,
    METHOD,
    MUTANT,
    MUTANT_PATH,
    ORACLE,
    OUTPUT_TRANSFORM,
    RECIPE,
    RENDERED_NAME,
    SELECTION_PROCESSED,
    STAGES,
    assess,
    declared_log,
    display_transform,
    render_delivery,
    validate_document,
)
from decimal import Decimal


RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def load_document() -> dict:
    path = ROOT / "docs" / "P062_IMPLEMENT_DISPLAY_AND_LOG_EXPORT_BRANCHES.json"
    return json.loads(path.read_text(encoding="utf-8"))


class P062ExportBranchTests(unittest.TestCase):
    def assert_result(self, result) -> None:
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], "P062")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) and item for item in result[key]))

    def test_constants_encode_method_fixture_oracle_and_mutant(self) -> None:
        self.assertEqual(MAP_ID, "s23-display-and-log-export-branches-fixture")
        self.assertEqual(BASE_REVISION, "d4deac8fc82832fd23396a01065c5f0bf9da6670")
        self.assertIn("clean Log export excludes film grain", METHOD)
        self.assertIn("explicitly named processed master", METHOD)
        self.assertEqual(
            FIXTURE,
            "A take exported once as a clean Log master and again with strong grain, "
            "halation, and virtual defocus.",
        )
        self.assertEqual(
            ORACLE,
            "The clean master remains unaffected while the rendered result records all "
            "processing stages.",
        )
        self.assertEqual(
            MUTANT,
            "Apply the display transform before both branches and call one output clean Log.",
        )
        self.assertEqual(EXCLUDED, ("film-grain", "halation", "virtual-lens", "display-tone-map"))
        self.assertEqual(STAGES, ("film-grain", "halation", "virtual-defocus", "output-transform"))
        self.assertEqual(ENCODING, "declared-log-fixture")
        self.assertNotEqual(ENCODING, "LogC3")

    def test_fixture_keeps_clean_log_off_the_rendered_recipe(self) -> None:
        raw = load_document()
        self.assertIsNone(validate_document(raw))
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P062")
        self.assertEqual(raw["mapId"], MAP_ID)
        self.assertEqual(raw["implementationBaseRevision"], BASE_REVISION)
        self.assertEqual(raw["method"], METHOD)
        self.assertEqual(raw["fixture"], FIXTURE)
        self.assertEqual(raw["oracle"], ORACLE)
        self.assertEqual(raw["mutant"], MUTANT)
        working = tuple(Decimal(item) for item in raw["workingImage"]["rgb"])
        clean = tuple(declared_log(channel) for channel in working)
        rendered = render_delivery(working)
        self.assertEqual(tuple(str(item) for item in clean), ("0.35", "0.85", "0.45"))
        self.assertEqual(tuple(str(item) for item in rendered), ("0.35", "1", "0.45"))
        self.assertNotEqual(clean, rendered)
        self.assertNotEqual(display_transform(working[1]), working[1])
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "branches_separated")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("working:take-working:0.2,1.2,0.4", result["preservedResults"])
        self.assertIn("clean:clean-log:0.35,0.85,0.45", result["preservedResults"])
        self.assertIn(
            "clean-excluded:film-grain,halation,virtual-lens,display-tone-map",
            result["preservedResults"],
        )
        self.assertIn("rendered:rendered-delivery:0.35,1,0.45", result["preservedResults"])
        self.assertIn(
            "rendered-stages:film-grain,halation,virtual-defocus,output-transform",
            result["preservedResults"],
        )
        self.assertIn("recipe:" + RECIPE, result["preservedResults"])
        self.assertIn("output-transform:" + OUTPUT_TRANSFORM, result["preservedResults"])
        self.assertIn("encoding:" + ENCODING, result["preservedResults"])
        self.assertIn("display-working:not-applied", result["preservedResults"])
        self.assertIn("contaminated-clean:not-applied", result["preservedResults"])
        self.assertNotIn("clean:clean-log:0.35,0.75,0.45", result["preservedResults"])
        self.assertIn(ORACLE, result["reasons"])
        self.assertIn(HOST_LIMIT, result["reasons"])
        self.assertNotIn(MUTANT, result["reasons"])
        self.assertEqual(raw["cleanLog"]["name"], CLEAN_NAME)
        self.assertEqual(raw["rendered"]["name"], RENDERED_NAME)

    def test_mutant_display_before_both_is_not_clean_log(self) -> None:
        raw = load_document()
        honest = assess(raw)
        mutant = assess(raw, path=MUTANT_PATH)
        self.assert_result(mutant)
        self.assertEqual(honest["decision"], "branches_separated")
        self.assertEqual(mutant["decision"], "rejected")
        self.assertEqual(mutant["rejectedClaims"], ["display-before-both", "false-clean-log"])
        self.assertNotIn(mutant["decision"], {"qualified", "allowed", "branches_separated"})
        self.assertIn("clean:clean-log:0.35,0.85,0.45", mutant["preservedResults"])
        self.assertIn("rendered:rendered-delivery:0.35,1,0.45", mutant["preservedResults"])
        self.assertIn("working:take-working:0.2,1.2,0.4", mutant["preservedResults"])
        self.assertIn("display-working:0.2,1,0.4", mutant["preservedResults"])
        self.assertIn("contaminated-clean:0.35,0.75,0.45", mutant["preservedResults"])
        self.assertIn("contaminated-rendered:0.35,0.8,0.45", mutant["preservedResults"])
        self.assertIn(
            "rendered-stages:film-grain,halation,virtual-defocus,output-transform",
            mutant["preservedResults"],
        )
        self.assertIn(MUTANT, mutant["reasons"])
        self.assertIn("display transform before both branches was rejected", mutant["openQuestions"])
        self.assertNotEqual(honest["decision"], mutant["decision"])
        self.assertNotEqual(
            [item for item in honest["preservedResults"] if item.startswith("contaminated-clean:")],
            [item for item in mutant["preservedResults"] if item.startswith("contaminated-clean:")],
        )

    def test_processed_master_is_named_and_does_not_replace_clean_log(self) -> None:
        raw = load_document()
        result = assess(raw, selection=SELECTION_PROCESSED)
        self.assert_result(result)
        self.assertEqual(result["decision"], "processed_master_named")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("clean:clean-log:0.35,0.85,0.45", result["preservedResults"])
        self.assertIn("rendered:rendered-delivery:0.35,1,0.45", result["preservedResults"])
        self.assertIn("selection:processed-master", result["preservedResults"])
        self.assertIn(
            "processed master is explicitly named and is not a clean Log export",
            result["openQuestions"],
        )
        self.assertNotIn(result["decision"], {"qualified", "allowed", "branches_separated"})

    def test_invalid_documents_raise(self) -> None:
        valid = load_document()
        extra = copy.deepcopy(valid)
        extra["note"] = "device"
        missing = copy.deepcopy(valid)
        del missing["mutant"]
        bad_phase = copy.deepcopy(valid)
        bad_phase["phase"] = "P061"
        logc = copy.deepcopy(valid)
        logc["cleanLog"]["encoding"] = "LogC3"
        stages = copy.deepcopy(valid)
        stages["rendered"]["stages"] = ["display-tone-map", "film-grain"]
        cases = (None, [], {}, extra, missing, bad_phase, logc, stages)
        for sample in cases:
            with self.subTest(sample=type(sample).__name__):
                with self.assertRaises(ValueError):
                    validate_document(sample)
        with self.assertRaises(ValueError):
            assess(valid, path="qualified")
        with self.assertRaises(ValueError):
            assess(valid, selection="allowed")


if __name__ == "__main__":
    unittest.main()
