"""Host checks for the P067 precision budget. Not a physical S23 probe.

TC-P067-01..08 are specified elsewhere and are not executed by this module.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "gates"))

from p067_validate_half_and_full_precision_boundaries import (  # noqa: E402
    BASE_REVISION,
    FIXTURE,
    HOST_LIMIT,
    MAP_ID,
    METHOD,
    MUTANT,
    MUTANT_PATH,
    ORACLE,
    absolute_error,
    assess,
    operation_faults,
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
    path = ROOT / "docs" / "P067_VALIDATE_HALF_AND_FULL_PRECISION_BOUNDARIES.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _op(preserved: list[str], op_id: str) -> str:
    return next(item for item in preserved if item.startswith(f"op:{op_id}:"))


class P067PrecisionBoundaryTests(unittest.TestCase):
    def assert_result(self, result) -> None:
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], "P067")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) and item for item in result[key]))

    def test_constants_encode_method_fixture_oracle_and_mutant(self) -> None:
        self.assertEqual(MAP_ID, "s23-precision-boundary-fixture")
        self.assertEqual(BASE_REVISION, "d4deac8fc82832fd23396a01065c5f0bf9da6670")
        self.assertIn("CPU double references", METHOD)
        self.assertIn("signed dark values", METHOD)
        self.assertIn("bright highlights", METHOD)
        self.assertIn("matrix cancellation", METHOD)
        self.assertIn("long accumulations", METHOD)
        self.assertIn("overflow", METHOD)
        self.assertIn("denormal", METHOD)
        self.assertIn("texture conversion", METHOD)
        self.assertIn("explicit graph decisions", METHOD)
        self.assertEqual(
            FIXTURE,
            "A bright narrow highlight convolved with a large kernel and a near-neutral "
            "matrix cancellation case.",
        )
        self.assertEqual(
            ORACLE,
            "The chosen precision stays within the declared error budget or the graph "
            "promotes the affected operation.",
        )
        self.assertEqual(MUTANT, "Replace every intermediate with FP16 without testing accumulated error.")

    def test_fixture_stays_inside_budget_or_promotes(self) -> None:
        raw = load_document()
        self.assertIsNone(validate_document(raw))
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P067")
        self.assertEqual(raw["mapId"], MAP_ID)
        self.assertEqual(raw["implementationBaseRevision"], BASE_REVISION)
        self.assertEqual(raw["method"], METHOD)
        self.assertEqual(raw["fixture"], FIXTURE)
        self.assertEqual(raw["oracle"], ORACLE)
        self.assertEqual(raw["mutant"], MUTANT)
        self.assertEqual(raw["suite"]["reference"], "cpu-double")
        self.assertEqual(raw["suite"]["compared"], "gpu-output")
        self.assertIs(raw["suite"]["framesProcessed"], False)
        faults = {item["id"]: operation_faults(item) for item in raw["operations"]}
        self.assertTrue(all(item == [] for item in faults.values()))
        self.assertEqual(absolute_error("18.75", "18.7502"), "0.0002")
        self.assertEqual(absolute_error("0.0004", "0.00041"), "0.00001")
        self.assertEqual(absolute_error("-0.02", "-0.02001"), "0.00001")
        self.assertEqual(absolute_error("0.5", "0.5004"), "0.0004")
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "precision_bounded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "rejected"})
        self.assertIn(ORACLE, result["reasons"])
        self.assertIn(HOST_LIMIT, result["reasons"])
        self.assertNotIn(MUTANT, result["reasons"])
        self.assertIn(
            "highlight kernel and matrix cancellation stayed inside the budget or were promoted",
            result["reasons"],
        )
        preserved = result["preservedResults"]
        self.assertIn(
            "suite:reference=cpu-double:compared=gpu-output:frames-processed=false",
            preserved,
        )
        self.assertIn("cpu=-0.02", _op(preserved, "signed-dark"))
        self.assertIn("gpu=-0.02001", _op(preserved, "signed-dark"))
        self.assertIn("error=0.00001", _op(preserved, "signed-dark"))
        self.assertIn("status=within-budget", _op(preserved, "signed-dark"))
        self.assertIn("chosen=fp32", _op(preserved, "highlight-kernel"))
        self.assertIn("cpu=18.75", _op(preserved, "highlight-kernel"))
        self.assertIn("gpu=18.7502", _op(preserved, "highlight-kernel"))
        self.assertIn("budget=0.001", _op(preserved, "highlight-kernel"))
        self.assertIn("error=0.0002", _op(preserved, "highlight-kernel"))
        self.assertIn("status=promoted", _op(preserved, "highlight-kernel"))
        self.assertIn("cpu=0.0004", _op(preserved, "matrix-cancellation"))
        self.assertIn("gpu=0.00041", _op(preserved, "matrix-cancellation"))
        self.assertIn("error=0.00001", _op(preserved, "matrix-cancellation"))
        self.assertIn("status=promoted", _op(preserved, "matrix-cancellation"))
        self.assertIn("chosen=fp16", _op(preserved, "texture-conversion"))
        self.assertIn("explicit=true", _op(preserved, "texture-conversion"))
        self.assertIn("tested=true", _op(preserved, "texture-conversion"))
        self.assertIn("status=within-budget", _op(preserved, "texture-conversion"))
        self.assertIn("overflow=true", _op(preserved, "overflow-guard"))
        self.assertIn("status=promoted", _op(preserved, "overflow-guard"))
        self.assertIn("denormal=true", _op(preserved, "denormal-guard"))
        self.assertIn("status=promoted", _op(preserved, "denormal-guard"))
        self.assertIn("probe=long-accumulation", _op(preserved, "long-accumulation"))
        self.assertIn("probe=bright-highlight", _op(preserved, "bright-highlight"))

    def test_mutant_fp16_everywhere_is_rejected(self) -> None:
        raw = load_document()
        honest = assess(raw)
        mutant = assess(raw, path=MUTANT_PATH)
        self.assert_result(mutant)
        self.assertEqual(honest["decision"], "precision_bounded")
        self.assertEqual(mutant["decision"], "rejected")
        self.assertEqual(mutant["rejectedClaims"], ["fp16-without-accumulated-error"])
        self.assertNotIn(mutant["decision"], {"qualified", "allowed", "precision_bounded"})
        self.assertIn(MUTANT, mutant["reasons"])
        self.assertIn(
            "replacing every intermediate with FP16 does not test accumulated error",
            mutant["reasons"],
        )
        self.assertIn(
            "mutant FP16 replacement was rejected without erasing the differential inventory",
            mutant["openQuestions"],
        )
        honest_ops = [item for item in honest["preservedResults"] if item.startswith("op:")]
        mutant_ops = [item for item in mutant["preservedResults"] if item.startswith("op:")]
        self.assertEqual(honest_ops, mutant_ops)
        self.assertIn("chosen=fp32", _op(mutant["preservedResults"], "highlight-kernel"))
        self.assertIn("chosen=fp32", _op(mutant["preservedResults"], "matrix-cancellation"))
        self.assertIn("status=promoted", _op(mutant["preservedResults"], "highlight-kernel"))
        self.assertNotIn("chosen=fp16", _op(mutant["preservedResults"], "highlight-kernel"))

    def test_untested_fp16_on_the_declared_path_is_not_bounded(self) -> None:
        raw = load_document()
        raw["operations"] = [item for item in raw["operations"] if item["id"] == "texture-conversion"]
        tested = assess(raw)
        self.assertEqual(tested["decision"], "precision_bounded")
        self.assertEqual(tested["rejectedClaims"], [])
        raw["operations"][0]["accumulatedErrorTested"] = False
        mutant_data = assess(raw)
        self.assertEqual(mutant_data["decision"], "rejected")
        self.assertEqual(mutant_data["rejectedClaims"], ["texture-conversion"])
        self.assertIn(
            "texture-conversion rejected: untested-fp16, untested-texture-conversion",
            mutant_data["reasons"],
        )
        self.assertIn("tested=false", _op(mutant_data["preservedResults"], "texture-conversion"))
        self.assertIn("cpu=0.5", _op(mutant_data["preservedResults"], "texture-conversion"))
        self.assertNotIn(mutant_data["decision"], {"qualified", "allowed", "precision_bounded"})

    def test_over_budget_keeps_the_other_operations(self) -> None:
        raw = load_document()
        kernel = next(item for item in raw["operations"] if item["id"] == "highlight-kernel")
        kernel["gpuOutput"] = "19"
        kernel["promoted"] = False
        result = assess(raw)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["highlight-kernel"])
        self.assertIn("highlight-kernel rejected: over-budget", result["reasons"])
        self.assertIn("cpu=18.75", _op(result["preservedResults"], "highlight-kernel"))
        self.assertIn("gpu=19", _op(result["preservedResults"], "highlight-kernel"))
        self.assertIn("error=0.25", _op(result["preservedResults"], "highlight-kernel"))
        self.assertIn("status=rejected", _op(result["preservedResults"], "highlight-kernel"))
        self.assertIn("status=promoted", _op(result["preservedResults"], "matrix-cancellation"))
        self.assertIn("status=within-budget", _op(result["preservedResults"], "signed-dark"))
        self.assertNotIn(result["decision"], {"qualified", "allowed", "precision_bounded"})

    def test_silent_reduction_overflow_and_denormal_are_rejected(self) -> None:
        raw = load_document()
        raw["operations"] = [item for item in raw["operations"] if item["id"] == "signed-dark"]
        sample = raw["operations"][0]
        sample["chosenPrecision"] = "fp16"
        sample["requiredPrecision"] = "fp32"
        sample["explicitReduction"] = False
        sample["accumulatedErrorTested"] = True
        silent = assess(raw)
        self.assertEqual(silent["decision"], "rejected")
        self.assertEqual(silent["rejectedClaims"], ["signed-dark"])
        self.assertIn("signed-dark rejected: silent-reduction", silent["reasons"])
        self.assertIn("cpu=-0.02", _op(silent["preservedResults"], "signed-dark"))
        sample["explicitReduction"] = True
        sample["overflow"] = True
        sample["promoted"] = False
        overflow = assess(copy.deepcopy(raw))
        self.assertEqual(overflow["decision"], "rejected")
        self.assertIn("signed-dark rejected: unresolved-overflow", overflow["reasons"])
        sample["overflow"] = False
        sample["denormal"] = True
        denormal = assess(raw)
        self.assertEqual(denormal["decision"], "rejected")
        self.assertIn("signed-dark rejected: unresolved-denormal", denormal["reasons"])
        self.assertIn("denormal=true", _op(denormal["preservedResults"], "signed-dark"))

    def test_silent_texture_conversion_is_rejected(self) -> None:
        raw = load_document()
        raw["operations"] = [item for item in raw["operations"] if item["id"] == "texture-conversion"]
        raw["operations"][0]["explicitReduction"] = False
        result = assess(raw)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["texture-conversion"])
        self.assertIn(
            "texture-conversion rejected: silent-reduction, silent-texture-conversion",
            result["reasons"],
        )
        self.assertIn("texture=true", _op(result["preservedResults"], "texture-conversion"))
        self.assertIn("gpu=0.5004", _op(result["preservedResults"], "texture-conversion"))

    def test_device_frames_do_not_bound_a_passing_suite(self) -> None:
        raw = load_document()
        raw["suite"]["framesProcessed"] = True
        result = assess(raw)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["device-frames-claimed"])
        self.assertIn(
            "suite:reference=cpu-double:compared=gpu-output:frames-processed=true",
            result["preservedResults"],
        )
        self.assertIn("status=promoted", _op(result["preservedResults"], "highlight-kernel"))
        self.assertNotIn(result["decision"], {"qualified", "allowed", "precision_bounded"})

    def test_empty_operations_are_withheld_and_keep_the_suite(self) -> None:
        raw = load_document()
        raw["operations"] = []
        result = assess(raw)
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(
            result["preservedResults"],
            ["suite:reference=cpu-double:compared=gpu-output:frames-processed=false"],
        )
        self.assertIn("no differential operations were supplied", result["openQuestions"])

    def test_invalid_documents_raise(self) -> None:
        valid = load_document()
        extra = copy.deepcopy(valid)
        extra["note"] = "device"
        missing = copy.deepcopy(valid)
        del missing["mutant"]
        bad_phase = copy.deepcopy(valid)
        bad_phase["phase"] = "P066"
        bad_revision = copy.deepcopy(valid)
        bad_revision["implementationBaseRevision"] = "abc"
        bad_reference = copy.deepcopy(valid)
        bad_reference["suite"]["reference"] = "gpu-output"
        string_flag = copy.deepcopy(valid)
        string_flag["suite"]["framesProcessed"] = "false"
        trailing = copy.deepcopy(valid)
        trailing["operations"][0]["cpuDouble"] = "-0.02000"
        zero_budget = copy.deepcopy(valid)
        zero_budget["operations"][0]["errorBudget"] = "0"
        duplicate = copy.deepcopy(valid)
        duplicate["operations"].append(copy.deepcopy(duplicate["operations"][0]))
        bad_probe = copy.deepcopy(valid)
        bad_probe["operations"][0]["probe"] = "cinema"
        false_explicit = copy.deepcopy(valid)
        false_explicit["operations"][0]["explicitReduction"] = True
        empty_ops_type = copy.deepcopy(valid)
        empty_ops_type["operations"] = None
        cases = (
            None,
            [],
            {},
            extra,
            missing,
            bad_phase,
            bad_revision,
            bad_reference,
            string_flag,
            trailing,
            zero_budget,
            duplicate,
            bad_probe,
            false_explicit,
            empty_ops_type,
        )
        for sample in cases:
            with self.subTest(sample=type(sample).__name__):
                with self.assertRaises(ValueError):
                    validate_document(sample)
        with self.assertRaises(ValueError):
            assess(valid, path="qualified")
        with self.assertRaises(ValueError):
            assess(valid, path="allowed")


if __name__ == "__main__":
    unittest.main()
