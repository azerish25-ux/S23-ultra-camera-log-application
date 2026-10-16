"""Host checks for P104 integrated depth performance. Not a physical S23 probe."""

from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "p104_qualify_integrated_depth_performance_on_the_s23",
    Path(__file__).resolve().parents[1] / "gates" / "p104_qualify_integrated_depth_performance_on_the_s23.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
assess = _MODULE.assess
evaluate = _MODULE.evaluate
sample_total_ms = _MODULE.sample_total_ms
frame_interval_ms = _MODULE.frame_interval_ms
over_budget_fraction = _MODULE.over_budget_fraction

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
ROOT = Path(__file__).resolve().parents[2]


def document(**overrides):
    value = {
        "schemaVersion": 1,
        "phase": "P104",
        "implementationBaseRevision": "3fbad4bc0e0336e273d2723ec873f001e8865323",
        "evidenceId": "p104-integrated-budget",
        "device": "s23",
        "measured_on_device": False,
        "physical_qualification": "unavailable",
        "measurement_id": None,
        "fps": 24,
        "input_resolution": "1280x720",
        "inference_cadence_hz": 8,
        "output_resolution": "3840x2160",
        "thermal": "warm",
        "memory": "pressure",
        "live_depth": "deferred_only",
        "dropped_frames": 3,
        "hide_dropped_frames": False,
        "frame_rate_source": "integrated",
        "samples": [
            {"capture_ms": 20, "inference_ms": 5, "render_ms": 20, "encode_ms": 10},
            {"capture_ms": 8, "inference_ms": 4, "render_ms": 10, "encode_ms": 8},
            {"capture_ms": 15, "inference_ms": 6, "render_ms": 18, "encode_ms": 12},
            {"capture_ms": 10, "inference_ms": 3, "render_ms": 12, "encode_ms": 10},
            {"capture_ms": 12, "inference_ms": 4, "render_ms": 14, "encode_ms": 16},
        ],
    }
    value.update(overrides)
    return value


class P104IntegratedDepthTests(unittest.TestCase):
    def assert_contract(self, result, evidence="p104-integrated-budget"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "P104")
        self.assertIn(result["decision"], {"recorded", "rejected"})
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertEqual(result["openQuestions"][0], "physical S23 measurement was not run")
        self.assertTrue(any(item.startswith("dropped-frames:") for item in result["preservedResults"]))

    def test_constants_match_the_spec(self):
        self.assertEqual(_MODULE.BASE_REVISION, "3fbad4bc0e0336e273d2723ec873f001e8865323")
        self.assertEqual(_MODULE.PHASE, "P104")
        self.assertEqual(_MODULE.WORKSTREAM, 13)
        self.assertEqual(_MODULE.DEPENDENCIES, ("P103",))
        self.assertEqual(_MODULE.TITLE, "Qualify integrated depth performance on the S23")
        self.assertEqual(_MODULE.GOAL, "Decide what can run live and what belongs in deferred development.")
        self.assertIn("Record input resolution and inference cadence separately", _MODULE.METHOD)
        self.assertEqual(
            _MODULE.FIXTURE,
            "A model that runs quickly when isolated but reduces recording stability during a sustained take.",
        )
        self.assertEqual(
            _MODULE.ORACLE,
            "The scheduler chooses a lower-cost preview or deferred-only policy rather than hiding dropped source frames.",
        )
        self.assertEqual(
            _MODULE.MUTANT,
            "Advertise model inference rate as full-resolution rendered recording rate.",
        )
        self.assertEqual(_MODULE.DELIVERABLE, "Physical inference qualification and live-versus-deferred decision")

    def test_budget_math_sums_stages_and_counts_over_interval(self):
        samples = document()["samples"]
        self.assertEqual([sample_total_ms(sample) for sample in samples], [55.0, 30.0, 51.0, 35.0, 46.0])
        self.assertEqual(frame_interval_ms(24), 1000 / 24)
        self.assertEqual(over_budget_fraction(samples, 24), 0.6)
        self.assertEqual(over_budget_fraction(samples, 24), 3 / 5)
        self.assertGreater(sample_total_ms(samples[0]), samples[0]["inference_ms"])
        equal = [{"capture_ms": 10, "inference_ms": 10, "render_ms": 10, "encode_ms": 10}]
        self.assertEqual(sample_total_ms(equal[0]), 40.0)
        self.assertEqual(frame_interval_ms(25), 40.0)
        self.assertEqual(over_budget_fraction(equal, 25), 0.0)

    def test_good_unavailable_s23_is_recorded_not_qualified(self):
        raw = json.loads(
            (ROOT / "docs" / "P104_QUALIFY_INTEGRATED_DEPTH_PERFORMANCE_ON_THE_S23.json").read_text(encoding="utf-8")
        )
        result = assess(raw)
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn(_MODULE.ORACLE, result["reasons"])
        preserved = result["preservedResults"]
        self.assertIn("dropped-frames:3", preserved)
        self.assertIn("over-budget:3/5", preserved)
        self.assertIn("over-budget-fraction:0.6", preserved)
        self.assertIn("frame-interval:1000/24", preserved)
        self.assertIn("sample:0:total-ms:55:inference-ms:5:over-budget:true", preserved)
        self.assertIn("sample:1:total-ms:30:inference-ms:4:over-budget:false", preserved)
        self.assertIn("input-resolution:1280x720", preserved)
        self.assertIn("inference-cadence-hz:8", preserved)
        self.assertIn("output-resolution:3840x2160", preserved)
        self.assertIn("output-fps:24", preserved)
        self.assertIn("device:s23", preserved)
        self.assertIn("measured-on-device:false", preserved)
        self.assertIn("physical-qualification:unavailable", preserved)
        self.assertIn("live-depth:deferred_only", preserved)
        self.assertNotIn("sample:0:total-ms:5:inference-ms:5:over-budget:true", preserved)
        self.assertEqual(evaluate(raw), result)

    def test_negative_inference_fps_claim_keeps_the_integrated_budget(self):
        result = assess(document(frame_rate_source="inference"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.MUTANT, result["rejectedClaims"])
        self.assertIn("standalone-inference-as-camera-fps", result["rejectedClaims"])
        self.assertIn("over-budget-fraction:0.6", result["preservedResults"])
        self.assertIn("dropped-frames:3", result["preservedResults"])
        self.assertIn("sample:0:total-ms:55:inference-ms:5:over-budget:true", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_negative_physical_claim_without_measurement_id_is_rejected(self):
        result = assess(document(physical_qualification="claimed"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("unmeasured-physical-qualification", result["rejectedClaims"])
        self.assertIn("physical-qualification-not-measured-on-device", result["rejectedClaims"])
        self.assertIn("dropped-frames:3", result["preservedResults"])
        claimed = assess(document(physical_qualification="qualified", measurement_id="m-1"))
        self.assertEqual(claimed["decision"], "rejected")
        self.assertNotEqual(claimed["decision"], "qualified")
        self.assertIn("physical-qualification-not-measured-on-device", claimed["rejectedClaims"])
        self.assertNotIn("unmeasured-physical-qualification", claimed["rejectedClaims"])

    def test_severe_thermal_or_memory_cannot_stay_live(self):
        live = assess(document(thermal="severe", live_depth="live", dropped_frames=0))
        self.assertEqual(live["decision"], "rejected")
        self.assertIn("live-under-severe", live["rejectedClaims"])
        self.assertIn("dropped-frames:0", live["preservedResults"])
        memory = assess(document(memory="severe", live_depth="live", dropped_frames=0))
        self.assertIn("live-under-severe", memory["rejectedClaims"])
        preview = assess(document(thermal="severe", live_depth="lower_cost_preview"))
        self.assertEqual(preview["decision"], "rejected")
        self.assertIn("severe-requires-deferred-only", preview["rejectedClaims"])
        deferred = assess(document(thermal="severe", live_depth="deferred_only"))
        self.assertEqual(deferred["decision"], "recorded")
        self.assertEqual(deferred["rejectedClaims"], [])
        self.assertIn("thermal:severe", deferred["preservedResults"])

    def test_hidden_dropped_frames_are_still_preserved(self):
        result = assess(document(hide_dropped_frames=True, dropped_frames=7))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("hidden-dropped-frames", result["rejectedClaims"])
        self.assertIn("dropped-frames:7", result["preservedResults"])
        self.assertIn("hide-dropped-frames:true", result["preservedResults"])

    def test_live_over_budget_is_rejected_and_lower_cost_preview_is_recorded(self):
        live = assess(document(live_depth="live"))
        self.assertEqual(live["decision"], "rejected")
        self.assertIn("live-despite-integrated-over-budget", live["rejectedClaims"])
        self.assertIn("live-while-dropping-source-frames", live["rejectedClaims"])
        preview = assess(document(live_depth="lower_cost_preview"))
        self.assertEqual(preview["decision"], "recorded")
        self.assertIn("live-depth:lower_cost_preview", preview["preservedResults"])
        self.assertIn("dropped-frames:3", preview["preservedResults"])

    def test_evidence_change_is_preserved(self):
        evidence = "p104-evidence-changed"
        result = assess(document(evidenceId=evidence))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["preservedResults"][0], evidence)

    def test_within_budget_live_is_recorded_not_qualified(self):
        samples = [
            {"capture_ms": 5, "inference_ms": 2, "render_ms": 5, "encode_ms": 5},
            {"capture_ms": 4, "inference_ms": 2, "render_ms": 4, "encode_ms": 4},
        ]
        self.assertEqual(over_budget_fraction(samples, 24), 0.0)
        result = assess(document(samples=samples, live_depth="live", dropped_frames=0, thermal="nominal", memory="nominal"))
        self.assertEqual(result["decision"], "recorded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("dropped-frames:0", result["preservedResults"])
        self.assertIn("over-budget:0/2", result["preservedResults"])
        self.assertIn("over-budget-fraction:0", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = document()
        extra = copy.deepcopy(valid)
        extra["applyNegative"] = True
        nan = copy.deepcopy(valid)
        nan["samples"] = [{"capture_ms": 1, "inference_ms": float("nan"), "render_ms": 1, "encode_ms": 1}]
        cases = (
            None,
            {},
            [],
            extra,
            {k: v for k, v in valid.items() if k != "samples"},
            document(phase="P103"),
            document(implementationBaseRevision="abc"),
            document(fps=0),
            document(dropped_frames=-1),
            document(dropped_frames=True),
            document(measured_on_device=0),
            document(device="S23"),
            document(physical_qualification="yes"),
            document(measurement_id=""),
            nan,
            document(samples=[]),
            document(samples=[{"capture_ms": 1, "inference_ms": 1, "render_ms": 1}]),
        )
        for sample in cases:
            with self.subTest(sample=type(sample).__name__):
                with self.assertRaises(ValueError):
                    assess(sample)
                with self.assertRaises(ValueError):
                    evaluate(sample)


if __name__ == "__main__":
    unittest.main()
