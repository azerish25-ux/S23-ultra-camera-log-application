"""Host checks for the P014 high-resolution experiment matrix.

Not a physical S23 probe. TC-P014-01..08 are specified elsewhere and are not
executed by this module.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "gates"))

from p008_protocol import validate_handoff
from p014_plan_native_high_resolution_experiments import (
    BASE_REVISION,
    EXPERIMENTS,
    FIXTURE,
    METHOD,
    MUTANT,
    MUTANT_CLAIM,
    ORACLE,
    RESULT_KEYS,
    assess_candidate,
    assess_matrix,
    export_candidates,
    native_8k_accepted,
    validate_matrix,
)


FORBIDDEN = {"qualified", "allowed", "native_8k"}


def load_matrix() -> dict:
    path = ROOT / "docs" / "P014_PLAN_NATIVE_HIGH_RESOLUTION_EXPERIMENTS.json"
    return json.loads(path.read_text(encoding="utf-8"))


def load_handoff() -> dict:
    path = ROOT / "docs" / "evidence" / "P014-handoff.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _experiments(status: str = "unmeasured") -> dict:
    return {name: status for name in EXPERIMENTS}


def candidate(**overrides) -> dict:
    value = {
        "tupleId": "native-4k",
        "advertised": True,
        "userTarget": True,
        "sourceWidth": 3840,
        "sourceHeight": 2160,
        "outputWidth": 3840,
        "outputHeight": 2160,
        "containerWidth": 3840,
        "containerHeight": 2160,
        "transform": "native",
        "rendererEnlarged": False,
        "experiments": _experiments(),
    }
    value.update(overrides)
    return value


def upscaled_8k(**overrides) -> dict:
    value = candidate(
        tupleId="8k-upscaled-7680x4320",
        sourceWidth=3840,
        sourceHeight=2160,
        outputWidth=7680,
        outputHeight=4320,
        containerWidth=7680,
        containerHeight=4320,
        transform="upscale",
        rendererEnlarged=True,
    )
    value.update(overrides)
    return value


def matrix(candidates: list[dict], **overrides) -> dict:
    value = {
        "schemaVersion": 1,
        "phase": "P014",
        "matrixId": "s23-high-resolution-experiment-matrix",
        "implementationBaseRevision": BASE_REVISION,
        "method": METHOD,
        "fixture": FIXTURE,
        "oracle": ORACLE,
        "mutant": MUTANT,
        "requiredExperiments": list(EXPERIMENTS),
        "candidates": candidates,
    }
    value.update(overrides)
    return value


def _container_only_mutant(item: dict) -> bool:
    """The forbidden implementation: container width and height alone."""
    return item["containerWidth"] == 7680 and item["containerHeight"] == 4320


class P014HighResolutionExperimentTests(unittest.TestCase):
    def assert_contract(self, result: dict) -> None:
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], "P014")
        self.assertNotIn(result["decision"], FORBIDDEN)
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) and item for item in result[key]))

    def test_module_encodes_method_fixture_oracle_and_mutant(self) -> None:
        self.assertIn("advertised sizes", METHOD)
        self.assertIn("user targets", METHOD)
        self.assertIn("capture, encode, decode, cadence, storage", METHOD)
        self.assertIn("thermal experiments", METHOD)
        self.assertIn("crop, binning, downsampling, and upscaling", METHOD)
        self.assertIn("7680 by 4320", FIXTURE)
        self.assertIn("smaller stream enlarged", FIXTURE)
        self.assertIn("upscaled output", ORACLE)
        self.assertIn("native 8K acceptance requirement", ORACLE)
        self.assertEqual(MUTANT, "Validate native resolution using only the container width and height.")

    def test_fixture_labels_renderer_enlarged_7680_as_upscaled(self) -> None:
        raw = load_matrix()
        self.assertIsNone(validate_matrix(raw))
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P014")
        self.assertEqual(raw["matrixId"], "s23-high-resolution-experiment-matrix")
        self.assertEqual(raw["implementationBaseRevision"], BASE_REVISION)
        self.assertEqual(raw["method"], METHOD)
        self.assertEqual(raw["fixture"], FIXTURE)
        self.assertEqual(raw["oracle"], ORACLE)
        self.assertEqual(raw["mutant"], MUTANT)
        self.assertEqual(raw["requiredExperiments"], list(EXPERIMENTS))
        exported = export_candidates(raw)
        self.assertEqual(len(exported), len(raw["candidates"]))
        by_id = {item["tupleId"]: item for item in exported}
        self.assertEqual(by_id["4k-3840x2160"]["geometry"], "native")
        self.assertEqual(by_id["4k-3840x2160"]["source"], "3840x2160")
        self.assertIs(by_id["4k-3840x2160"]["userTarget"], True)
        self.assertIs(by_id["4k-3840x2160"]["native8kAccepted"], False)
        enlarged = by_id["8k-upscaled-7680x4320"]
        self.assertEqual(enlarged["geometry"], "upscaled output")
        self.assertEqual(enlarged["source"], "3840x2160")
        self.assertEqual(enlarged["output"], "7680x4320")
        self.assertEqual(enlarged["container"], "7680x4320")
        self.assertIs(enlarged["native8kAccepted"], False)
        self.assertIn("crop-4000x3000-to-3840x2160", by_id)
        self.assertIn("binning-3840x2160-to-1920x1080", by_id)
        self.assertIn("downsample-1920x1080-to-1280x720", by_id)
        self.assertTrue(all(item["native8kAccepted"] is False for item in exported))
        result = assess_matrix(raw)
        self.assert_contract(result)
        self.assertEqual(result["decision"], "upscaled")
        self.assertIn(ORACLE, result["reasons"])
        self.assertIn("upscaled output", result["reasons"])
        self.assertEqual(result["rejectedClaims"][:2], ["native-8k", "physical-s23"])
        self.assertIn("container-as-source", result["rejectedClaims"])
        self.assertIn("tuple:4k-3840x2160", result["preservedResults"])
        self.assertIn("tuple:8k-upscaled-7680x4320", result["preservedResults"])
        self.assertIn("source:3840x2160", result["preservedResults"])
        self.assertIn("geometry:native", result["preservedResults"])
        self.assertIn("geometry:crop", result["preservedResults"])
        self.assertIn("geometry:binning", result["preservedResults"])
        self.assertIn("geometry:downsample", result["preservedResults"])
        self.assertIn("container:7680x4320", result["preservedResults"])
        for name in EXPERIMENTS:
            self.assertIn(f"{name} experiment is unmeasured", result["openQuestions"])
        self.assertIn("physical S23 qualification remains open", result["openQuestions"])

    def test_container_dimensions_alone_do_not_accept_native_8k(self) -> None:
        raw = load_matrix()
        enlarged = next(item for item in raw["candidates"] if item["tupleId"] == "8k-upscaled-7680x4320")
        self.assertTrue(_container_only_mutant(enlarged))
        self.assertFalse(native_8k_accepted(enlarged))
        self.assertNotEqual(native_8k_accepted(enlarged), _container_only_mutant(enlarged))
        declared = upscaled_8k(experiments=_experiments("measured"))
        self.assertTrue(_container_only_mutant(declared))
        self.assertFalse(native_8k_accepted(declared))
        native_container = candidate(
            tupleId="container-says-8k",
            sourceWidth=1920,
            sourceHeight=1080,
            outputWidth=1920,
            outputHeight=1080,
            containerWidth=7680,
            containerHeight=4320,
            transform="native",
            rendererEnlarged=False,
            experiments=_experiments("measured"),
        )
        document = matrix([native_container, upscaled_8k()])
        self.assertIsNone(validate_matrix(document))
        self.assertFalse(native_8k_accepted(native_container))
        withheld = assess_candidate(document, "container-says-8k")
        self.assertEqual(withheld["decision"], "withheld")
        self.assertIn("container-as-source", withheld["rejectedClaims"])
        self.assertIn("native-8k", withheld["rejectedClaims"])
        self.assertIn("source:1920x1080", withheld["preservedResults"])
        self.assertNotIn(withheld["decision"], FORBIDDEN)

    def test_mutant_container_only_is_rejected_and_keeps_the_inventory(self) -> None:
        raw = load_matrix()
        honest = assess_matrix(raw)
        mutant = assess_matrix(raw, container_only=True)
        self.assert_contract(mutant)
        self.assertEqual(mutant["decision"], "rejected")
        self.assertNotIn(mutant["decision"], FORBIDDEN)
        self.assertEqual(mutant["rejectedClaims"][0], MUTANT_CLAIM)
        self.assertIn("native-8k", mutant["rejectedClaims"])
        self.assertEqual(mutant["preservedResults"], honest["preservedResults"])
        self.assertIn("tuple:4k-3840x2160", mutant["preservedResults"])
        self.assertTrue(any("container width and height" in item for item in mutant["reasons"]))
        self.assertIn(MUTANT, mutant["reasons"])
        enlarged = next(item for item in raw["candidates"] if item["rendererEnlarged"] is True)
        self.assertFalse(native_8k_accepted(enlarged))

    def test_measured_native_8k_marks_are_still_not_acceptance(self) -> None:
        native = candidate(
            tupleId="native-8k-unmeasured-host",
            sourceWidth=7680,
            sourceHeight=4320,
            outputWidth=7680,
            outputHeight=4320,
            containerWidth=7680,
            containerHeight=4320,
            transform="native",
            rendererEnlarged=False,
            experiments=_experiments("measured"),
            userTarget=True,
        )
        self.assertFalse(native_8k_accepted(native))
        self.assertTrue(_container_only_mutant(native))
        document = matrix([native, upscaled_8k()])
        one = assess_candidate(document, "native-8k-unmeasured-host")
        self.assert_contract(one)
        self.assertEqual(one["decision"], "recorded")
        self.assertIn("native-8k", one["rejectedClaims"])
        self.assertIn("source:7680x4320", one["preservedResults"])
        self.assertIn("tuple:native-8k-unmeasured-host", one["preservedResults"])
        for name in EXPERIMENTS:
            self.assertIn(f"{name}:measured", one["preservedResults"])
        self.assertTrue(any("not a physical S23 qualification" in item for item in one["reasons"]))
        exported = export_candidates(document)
        self.assertIs(exported[0]["native8kAccepted"], False)
        self.assertEqual(exported[1]["geometry"], "upscaled output")

    def test_unmeasured_4k_stays_visible_and_withheld(self) -> None:
        raw = load_matrix()
        result = assess_candidate(raw, "4k-3840x2160")
        self.assert_contract(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(
            result["preservedResults"][:5],
            [
                "source:3840x2160",
                "output:3840x2160",
                "container:3840x2160",
                "tuple:4k-3840x2160",
                "geometry:native",
            ],
        )
        self.assertTrue(any("4K and 8K ambitions" in item for item in result["reasons"]))
        crop = assess_candidate(raw, "crop-4000x3000-to-3840x2160")
        self.assertEqual(crop["decision"], "transformed")
        self.assertIn("native-acquisition", crop["rejectedClaims"])
        self.assertIn("source:4000x3000", crop["preservedResults"])
        self.assertIn("output:3840x2160", crop["preservedResults"])
        binned = assess_candidate(raw, "binning-3840x2160-to-1920x1080")
        self.assertEqual(binned["decision"], "transformed")
        self.assertIn("geometry:binning", binned["preservedResults"])
        down = assess_candidate(raw, "downsample-1920x1080-to-1280x720")
        self.assertEqual(down["decision"], "transformed")
        self.assertIn("output:1280x720", down["preservedResults"])

    def test_failed_experiment_rejects_native_tuple_without_dropping_geometry(self) -> None:
        failed = candidate(experiments={**_experiments("measured"), "thermal": "failed"})
        document = matrix([failed, upscaled_8k()])
        result = assess_candidate(document, "native-4k")
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("thermal-failed", result["rejectedClaims"])
        self.assertIn("source:3840x2160", result["preservedResults"])
        self.assertIn("thermal:failed", result["preservedResults"])
        self.assertIn("capture:measured", result["preservedResults"])

    def test_handoff_lists_cases_and_does_not_invent_a_commit(self) -> None:
        handoff = load_handoff()
        self.assertIsNone(validate_handoff(handoff))
        self.assertEqual(handoff["phase"], "P014")
        self.assertEqual(
            handoff["caseIds"],
            [f"TC-P014-0{index}" for index in range(1, 9)],
        )
        self.assertIsNone(handoff["commit"])
        self.assertEqual(handoff["nextPhase"], "blocked")
        self.assertEqual(handoff["failures"], [])
        self.assertIn(
            "python3 -m unittest discover -s scripts/tests -p 'test_p014*.py' -v",
            handoff["testsRun"],
        )
        self.assertTrue(any("physical S23" in item for item in handoff["unverified"]))
        self.assertTrue(any("native 8K" in item for item in handoff["unverified"]))
        owned = {
            "scripts/gates/p014_plan_native_high_resolution_experiments.py",
            "scripts/tests/test_p014_plan_native_high_resolution_experiments.py",
            "docs/P014_PLAN_NATIVE_HIGH_RESOLUTION_EXPERIMENTS.md",
            "docs/P014_PLAN_NATIVE_HIGH_RESOLUTION_EXPERIMENTS.json",
            "docs/evidence/P014-handoff.json",
        }
        self.assertTrue(owned <= set(handoff["changedFiles"]))

    def test_invalid_matrices_raise(self) -> None:
        valid = load_matrix()
        self.assertIsNone(validate_matrix(valid))
        extra = copy.deepcopy(valid)
        extra["note"] = "device probe"
        missing = copy.deepcopy(valid)
        del missing["mutant"]
        drifted = copy.deepcopy(valid)
        drifted["oracle"] = "qualified native 8K"
        wrong_phase = copy.deepcopy(valid)
        wrong_phase["phase"] = "P013"
        empty = copy.deepcopy(valid)
        empty["candidates"] = []
        duplicate = copy.deepcopy(valid)
        duplicate["candidates"].append(copy.deepcopy(duplicate["candidates"][0]))
        bad_status = copy.deepcopy(valid)
        bad_status["candidates"][0]["experiments"]["capture"] = "qualified"
        native_enlarged = copy.deepcopy(valid)
        native_enlarged["candidates"][0]["rendererEnlarged"] = True
        shrink_upscale = matrix([
            upscaled_8k(outputWidth=1920, outputHeight=1080, containerWidth=1920, containerHeight=1080),
            upscaled_8k(tupleId="keep-oracle"),
        ])
        cases = (
            None,
            [],
            {},
            extra,
            missing,
            drifted,
            wrong_phase,
            empty,
            duplicate,
            bad_status,
            native_enlarged,
            shrink_upscale,
            matrix([candidate()], schemaVersion=True),
            matrix([candidate()], matrixId="other"),
            matrix([candidate()], implementationBaseRevision="abc"),
            matrix([candidate()], method="probe the sensor"),
            matrix([candidate(width=3840)]),
            matrix([candidate(transform="scale")]),
            matrix([candidate(advertised=1)]),
        )
        for sample in cases:
            with self.subTest(sample=type(sample).__name__):
                with self.assertRaises(ValueError):
                    validate_matrix(sample)
        with self.assertRaises(ValueError):
            assess_matrix(valid, container_only="true")
        with self.assertRaises(ValueError):
            assess_candidate(valid, "missing-tuple")
        with self.assertRaises(ValueError):
            assess_matrix(matrix([candidate()]))
        two = matrix([upscaled_8k(), upscaled_8k(tupleId="also-upscaled")])
        self.assertIsNone(validate_matrix(two))
        with self.assertRaises(ValueError):
            assess_matrix(two)


if __name__ == "__main__":
    unittest.main()
