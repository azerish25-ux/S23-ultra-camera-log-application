"""Host checks for the P072 full-pipeline performance report. Not a physical S23 probe.

TC-P072-01..08 are specified elsewhere and are not executed by this module.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "gates"))

from p072_measure_full_pipeline_performance import (  # noqa: E402
    BASE_REVISION,
    FIXTURE,
    HOST_LIMIT,
    MAP_ID,
    METHOD,
    MUTANT,
    MUTANT_PATH,
    ORACLE,
    assess,
    measure,
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
    path = ROOT / "docs" / "P072_MEASURE_FULL_PIPELINE_PERFORMANCE.json"
    return json.loads(path.read_text(encoding="utf-8"))


class P072FullPipelinePerformanceTests(unittest.TestCase):
    def assert_result(self, result) -> None:
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], "P072")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) and item for item in result[key]))

    def test_constants_encode_method_fixture_oracle_and_mutant(self) -> None:
        self.assertEqual(MAP_ID, "s23-full-pipeline-performance-fixture")
        self.assertEqual(BASE_REVISION, "d4deac8fc82832fd23396a01065c5f0bf9da6670")
        self.assertIn("queue occupancy together", METHOD)
        self.assertIn("retain cold-start results separately", METHOD)
        self.assertIn("live and deferred modes as different workflows", METHOD)
        self.assertEqual(
            FIXTURE,
            "A fast standalone depth model whose integrated path stalls because of repeated "
            "format conversion and memory copies.",
        )
        self.assertEqual(
            ORACLE,
            "The report attributes the actual bottleneck and does not advertise standalone "
            "inference latency as camera frame rate.",
        )
        self.assertEqual(MUTANT, "Compute end-to-end performance from the fastest individual kernel.")

    def test_fixture_attributes_copies_not_inference_frame_rate(self) -> None:
        raw = load_document()
        self.assertIsNone(validate_document(raw))
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P072")
        self.assertEqual(raw["mapId"], MAP_ID)
        self.assertEqual(raw["implementationBaseRevision"], BASE_REVISION)
        self.assertEqual(raw["method"], METHOD)
        self.assertEqual(raw["fixture"], FIXTURE)
        self.assertEqual(raw["oracle"], ORACLE)
        self.assertEqual(raw["mutant"], MUTANT)
        measured = measure(raw)
        self.assertEqual(measured["integrated"], "92.75")
        self.assertEqual(measured["bottleneck"], "copies")
        self.assertEqual(measured["bottleneckMs"], "46.5")
        self.assertEqual(measured["fastestStage"], "inference")
        self.assertEqual(measured["fastestMs"], "1.25")
        self.assertEqual(measured["cause"], "format-conversion")
        self.assertNotEqual(measured["integrated"], measured["fastestMs"])
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "bottleneck_attributed")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "rejected"})
        self.assertIn(ORACLE, result["reasons"])
        self.assertIn(HOST_LIMIT, result["reasons"])
        self.assertNotIn(MUTANT, result["reasons"])
        self.assertTrue(any("not a camera frame rate" in item for item in result["reasons"]))
        self.assertTrue(any("format conversion and memory copies" in item for item in result["reasons"]))
        preserved = result["preservedResults"]
        self.assertIn("model:standalone-depth:standalone-inference-ms=1.25:stall=true", preserved)
        self.assertIn("computed-bottleneck:copies", preserved)
        self.assertIn("computed-bottleneck-ms:46.5", preserved)
        self.assertIn("computed-cause:format-conversion", preserved)
        self.assertIn("computed-integrated-ms:92.75", preserved)
        self.assertIn("computed-fastest-stage:inference", preserved)
        self.assertIn("computed-fastest-kernel-ms:1.25", preserved)
        self.assertNotIn("computed-integrated-ms:1.25", preserved)
        self.assertIn("authored-frame-rate-source:integrated", preserved)
        self.assertIn("stage:copies:latency=46.5:occupancy=8", preserved)
        self.assertIn("stage:inference:latency=1.25:occupancy=1", preserved)
        self.assertIn("stage:capture:latency=8.4:occupancy=1", preserved)
        self.assertIn("stage:encoding:latency=11:occupancy=1", preserved)
        self.assertIn("stage:decoding:latency=4.8:occupancy=1", preserved)
        self.assertIn("stage:io:latency=13.6:occupancy=3", preserved)
        self.assertIn("stage:queue:latency=0:occupancy=9", preserved)
        self.assertIn("queue-occupancy:9", preserved)
        self.assertIn("conversion:depth-to-render:repeats=4:bytes=12582912", preserved)
        self.assertIn(
            "workflow:live:thermal=sustained:warmup=true:cold-retained=true:cold=180:sustained=92.75",
            preserved,
        )
        self.assertIn(
            "workflow:deferred:thermal=sustained:warmup=true:cold-retained=true:cold=240:sustained=61.4",
            preserved,
        )
        self.assertIn("priority:reduce-repeated-format-conversion", preserved)
        self.assertIn("priority:reduce-memory-copies", preserved)
        self.assertIn("priority:keep-standalone-inference-off-the-frame-rate-claim", preserved)
        self.assertIn("workflow-comparison:distinct", preserved)

    def test_mutant_fastest_kernel_is_not_end_to_end(self) -> None:
        raw = load_document()
        honest = assess(raw)
        mutant = assess(raw, path=MUTANT_PATH)
        self.assert_result(mutant)
        self.assertEqual(honest["decision"], "bottleneck_attributed")
        self.assertEqual(mutant["decision"], "rejected")
        self.assertEqual(mutant["rejectedClaims"], ["fastest-kernel-extrapolation"])
        self.assertNotIn(mutant["decision"], {"qualified", "allowed", "bottleneck_attributed"})
        self.assertIn(MUTANT, mutant["reasons"])
        self.assertIn("end-to-end performance was not computed from the fastest individual kernel", mutant["reasons"])
        self.assertIn("mutant fastest-kernel extrapolation was rejected", mutant["openQuestions"])
        self.assertIn("computed-integrated-ms:92.75", mutant["preservedResults"])
        self.assertIn("computed-fastest-kernel-ms:1.25", mutant["preservedResults"])
        self.assertIn("computed-bottleneck:copies", mutant["preservedResults"])
        self.assertNotIn("computed-integrated-ms:1.25", mutant["preservedResults"])
        self.assertIn("stage:inference:latency=1.25:occupancy=1", mutant["preservedResults"])
        self.assertIn("stage:copies:latency=46.5:occupancy=8", mutant["preservedResults"])
        self.assertEqual(
            [item for item in honest["preservedResults"] if item.startswith("stage:")],
            [item for item in mutant["preservedResults"] if item.startswith("stage:")],
        )
        self.assertIn("priority:reduce-repeated-format-conversion", mutant["preservedResults"])

    def test_standalone_inference_frame_rate_claim_is_rejected(self) -> None:
        raw = load_document()
        raw["attribution"]["frameRateSource"] = "standalone-inference"
        result = assess(raw)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["inference-as-frame-rate"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "bottleneck_attributed"})
        self.assertIn("authored-frame-rate-source:standalone-inference", result["preservedResults"])
        self.assertIn("computed-integrated-ms:92.75", result["preservedResults"])
        self.assertIn("computed-fastest-kernel-ms:1.25", result["preservedResults"])
        self.assertIn("stage:copies:latency=46.5:occupancy=8", result["preservedResults"])

    def test_misattribution_and_collapsed_workflows_keep_the_inventory(self) -> None:
        raw = load_document()
        raw["attribution"]["bottleneck"] = "inference"
        raw["attribution"]["cause"] = "stage-latency"
        raw["workflowComparison"] = "collapsed"
        result = assess(raw)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(
            result["rejectedClaims"],
            ["misattributed-bottleneck", "misattributed-cause", "collapsed-workflows"],
        )
        preserved = result["preservedResults"]
        self.assertIn("computed-bottleneck:copies", preserved)
        self.assertIn("authored-bottleneck:inference", preserved)
        self.assertIn("workflow-comparison:collapsed", preserved)
        self.assertIn(
            "workflow:live:thermal=sustained:warmup=true:cold-retained=true:cold=180:sustained=92.75",
            preserved,
        )
        self.assertIn(
            "workflow:deferred:thermal=sustained:warmup=true:cold-retained=true:cold=240:sustained=61.4",
            preserved,
        )
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_discarded_cold_start_and_unwarmed_sustained_are_rejected(self) -> None:
        raw = load_document()
        raw["workflows"][0]["coldStartRetained"] = False
        raw["workflows"][1]["warmup"] = False
        result = assess(raw)
        self.assertEqual(
            result["rejectedClaims"],
            ["discarded-cold-start:live", "sustained-without-warmup:deferred"],
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("cold-retained=false", " ".join(result["preservedResults"]))
        self.assertIn("cold=180", " ".join(result["preservedResults"]))
        self.assertIn("cold=240", " ".join(result["preservedResults"]))

    def test_live_sustained_must_match_the_integrated_sum(self) -> None:
        raw = load_document()
        raw["workflows"][0]["sustainedMs"] = "1.25"
        raw["workflows"][0]["coldStartMs"] = "2"
        result = assess(raw)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["live-sustained-mismatch"])
        self.assertIn("computed-integrated-ms:92.75", result["preservedResults"])
        self.assertIn("sustained=1.25", " ".join(result["preservedResults"]))
        self.assertNotIn("computed-integrated-ms:1.25", result["preservedResults"])

    def test_missing_sustained_thermal_state_is_withheld(self) -> None:
        raw = load_document()
        for workflow in raw["workflows"]:
            workflow["thermal"] = "cold"
            workflow["warmup"] = False
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("sustained thermal state was not reported", result["reasons"])
        self.assertIn("workflow:live:thermal=cold:warmup=false:cold-retained=true:cold=180:sustained=92.75", result["preservedResults"])
        self.assertIn("workflow:deferred:thermal=cold:warmup=false:cold-retained=true:cold=240:sustained=61.4", result["preservedResults"])
        self.assertIn("computed-bottleneck:copies", result["preservedResults"])
        mutant = assess(raw, path=MUTANT_PATH)
        self.assertEqual(mutant["decision"], "rejected")
        self.assertIn("fastest-kernel-extrapolation", mutant["rejectedClaims"])
        self.assertNotEqual(mutant["decision"], "bottleneck_attributed")

    def test_fastest_kernel_source_is_rejected_on_the_integrated_path(self) -> None:
        raw = load_document()
        raw["attribution"]["frameRateSource"] = "fastest-kernel"
        integrated = assess(raw)
        mutant = assess(raw, path=MUTANT_PATH)
        self.assertEqual(integrated["decision"], "rejected")
        self.assertEqual(integrated["rejectedClaims"], ["fastest-kernel-extrapolation"])
        self.assertEqual(mutant["rejectedClaims"], ["fastest-kernel-extrapolation"])
        self.assertNotIn(integrated["decision"], {"qualified", "allowed", "bottleneck_attributed"})
        self.assertIn("authored-frame-rate-source:fastest-kernel", integrated["preservedResults"])
        self.assertIn("computed-integrated-ms:92.75", mutant["preservedResults"])

    def test_invalid_documents_raise(self) -> None:
        valid = load_document()
        extra = copy.deepcopy(valid)
        extra["note"] = "device"
        missing = copy.deepcopy(valid)
        del missing["mutant"]
        bad_phase = copy.deepcopy(valid)
        bad_phase["phase"] = "P071"
        bad_revision = copy.deepcopy(valid)
        bad_revision["implementationBaseRevision"] = "abc"
        bad_method = copy.deepcopy(valid)
        bad_method["method"] = "fastest kernel only"
        swapped = copy.deepcopy(valid)
        swapped["stages"][1], swapped["stages"][2] = swapped["stages"][2], swapped["stages"][1]
        trailing = copy.deepcopy(valid)
        trailing["stages"][2]["latencyMs"] = "1.250"
        trailing["model"]["standaloneInferenceMs"] = "1.250"
        bool_stall = copy.deepcopy(valid)
        bool_stall["model"]["integratedStall"] = 1
        no_repeat = copy.deepcopy(valid)
        no_repeat["conversions"][0]["repeats"] = "1"
        slow_inference = copy.deepcopy(valid)
        slow_inference["stages"][2]["latencyMs"] = "80"
        slow_inference["model"]["standaloneInferenceMs"] = "80"
        equal_cold = copy.deepcopy(valid)
        equal_cold["workflows"][0]["coldStartMs"] = "92.75"
        collapsed_modes = copy.deepcopy(valid)
        collapsed_modes["workflows"][1]["mode"] = "live"
        empty_stages = copy.deepcopy(valid)
        empty_stages["stages"] = []
        cases = (
            None,
            [],
            {},
            extra,
            missing,
            bad_phase,
            bad_revision,
            bad_method,
            swapped,
            trailing,
            bool_stall,
            no_repeat,
            slow_inference,
            equal_cold,
            collapsed_modes,
            empty_stages,
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
