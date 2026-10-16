"""Host checks for P108. Not a physical S23 probe."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "p108_detect_occlusion_and_scene_discontinuities",
    Path(__file__).resolve().parents[1] / "gates" / "p108_detect_occlusion_and_scene_discontinuities.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
assess = _MODULE.assess
MUTANT = _MODULE.MUTANT
ORACLE = _MODULE.ORACLE
BASE_REVISION = _MODULE.BASE_REVISION
OPEN_QUESTION = _MODULE.OPEN_QUESTION

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
COUNT_KEYS = ("discontinuity_count", "occlusion_count", "unknown_count")


def document(**overrides):
    value = {
        "schemaVersion": 1,
        "phase": "P108",
        "implementationBaseRevision": BASE_REVISION,
        "evidenceId": "p108-hand-pan-cut",
        "claim": "occlusion-and-cut-host-fixture",
        "depthSamples": [1.0, 1.1, 3.4, 3.5],
        "threshold": 0.5,
        "flows": [
            {"dx": 0.3, "dy": 0.0, "rdx": -0.3, "rdy": 0.0},
            {"dx": 1.5, "dy": 0.2, "rdx": -0.1, "rdy": -0.2},
        ],
        "flow_threshold": 0.25,
        "smoothed": False,
        "sampleLabels": ["measured", "unknown", "measured", "measured"],
        "outputLabels": ["measured", "unknown", "measured", "measured"],
        "editBoundary": False,
        "timestampsContinuous": True,
        "carryHistory": False,
        "retainOccludedHistory": False,
    }
    value.update(overrides)
    return value


def retained_counts(result):
    counts = result["preservedResults"][2]
    if not isinstance(counts, dict):
        raise AssertionError("counts were not retained")
    return counts


class P108Tests(unittest.TestCase):
    def assert_contract(self, result, evidence="p108-hand-pan-cut"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "P108")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(result["decision"], {"recorded", "rejected"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("occlusion-and-cut-host-fixture", result["preservedResults"])
        self.assertIn(OPEN_QUESTION, result["openQuestions"])
        self.assertIn(ORACLE, " ".join(result["reasons"]))
        counts = retained_counts(result)
        self.assertEqual(tuple(counts), COUNT_KEYS)
        for key in COUNT_KEYS:
            self.assertIs(type(counts[key]), int)
            self.assertIn(f"{key}={counts[key]}", result["reasons"])

    def test_constants_match_the_phase_spec(self):
        self.assertEqual(BASE_REVISION, "3fbad4bc0e0336e273d2723ec873f001e8865323")
        self.assertEqual(_MODULE.PHASE, "P108")
        self.assertEqual(_MODULE.WORKSTREAM, 14)
        self.assertEqual(_MODULE.DEPENDENCIES, ("P107",))
        self.assertEqual(_MODULE.TITLE, "Detect occlusion and scene discontinuities")
        self.assertEqual(_MODULE.SLUG, "detect_occlusion_and_scene_discontinuities")
        self.assertEqual(_MODULE.GOAL, "Stop invalid temporal history from leaking across new surfaces or cuts.")
        self.assertEqual(
            _MODULE.MUTANT,
            "Carry temporal state across every clip boundary because timestamps are continuous.",
        )
        self.assertEqual(_MODULE.DELIVERABLE, "Occlusion mask and scene-reset tests")
        self.assertEqual(_MODULE.DEPTH_DISCONTINUITY_THRESHOLD, 0.5)
        self.assertEqual(_MODULE.FLOW_RESIDUAL_THRESHOLD, 0.25)
        self.assertEqual([case["id"] for case in _MODULE.CASES], [f"TC-P108-0{index}" for index in range(1, 9)])

    def test_detected_events_are_recorded_and_counts_stay(self):
        result = assess(document())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(
            retained_counts(result),
            {"discontinuity_count": 1, "occlusion_count": 1, "unknown_count": 1},
        )
        self.assertEqual(_MODULE.discontinuity_indexes([1.0, 1.1, 3.4, 3.5], 0.5), [2])
        self.assertEqual(
            _MODULE.occlusion_indexes(
                [
                    {"dx": 0.3, "dy": 0.0, "rdx": -0.3, "rdy": 0.0},
                    {"dx": 1.5, "dy": 0.2, "rdx": -0.1, "rdy": -0.2},
                ],
                0.25,
            ),
            [1],
        )

    def test_fixture_json_matches_the_recorded_host_observation(self):
        payload = json.loads(
            (_ROOT / "docs" / "P108_DETECT_OCCLUSION_AND_SCENE_DISCONTINUITIES.json").read_text()
        )
        result = assess(payload)
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(retained_counts(result)["discontinuity_count"], 1)
        self.assertEqual(retained_counts(result)["occlusion_count"], 1)
        self.assertEqual(retained_counts(result)["unknown_count"], 1)

    def test_threshold_equality_is_not_a_discontinuity_or_occlusion(self):
        result = assess(
            document(
                depthSamples=[0.0, 0.5, 1.0],
                threshold=0.5,
                flows=[{"dx": 0.25, "dy": 0.0, "rdx": 0.0, "rdy": 0.0}],
                flow_threshold=0.25,
                sampleLabels=["measured", "measured", "measured"],
                outputLabels=["measured", "measured", "measured"],
            )
        )
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(
            retained_counts(result),
            {"discontinuity_count": 0, "occlusion_count": 0, "unknown_count": 0},
        )
        self.assertFalse(_MODULE.flow_is_occlusion(0.25, 0.0, 0.0, 0.0, 0.25))
        self.assertTrue(_MODULE.flow_is_occlusion(0.25, 0.0, 0.01, 0.0, 0.25))
        self.assertTrue(_MODULE.flow_is_occlusion(0.0, 0.2, 0.0, 0.1, 0.25))

    def test_smoothing_across_a_discontinuity_is_rejected_and_evidence_remains(self):
        result = assess(document(smoothed=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("smoothing-across-discontinuity", result["rejectedClaims"])
        self.assertIn("p108-hand-pan-cut", result["preservedResults"])
        self.assertEqual(retained_counts(result)["discontinuity_count"], 1)
        self.assertEqual(retained_counts(result)["occlusion_count"], 1)
        self.assertEqual(retained_counts(result)["unknown_count"], 1)

    def test_filled_unknown_labelled_measured_is_rejected(self):
        result = assess(
            document(outputLabels=["measured", "measured", "measured", "measured"])
        )
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("filled-unknown-labelled-measured", result["rejectedClaims"])
        self.assertEqual(retained_counts(result)["unknown_count"], 1)

    def test_occluded_history_is_rejected(self):
        result = assess(document(retainOccludedHistory=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("occluded-history-retained", result["rejectedClaims"])
        self.assertEqual(retained_counts(result)["occlusion_count"], 1)

    def test_mutant_carry_across_a_cut_is_rejected_and_evidence_remains(self):
        result = assess(
            document(editBoundary=True, timestampsContinuous=True, carryHistory=True)
        )
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(MUTANT, result["rejectedClaims"])
        self.assertIn("p108-hand-pan-cut", result["preservedResults"])
        self.assertEqual(retained_counts(result)["discontinuity_count"], 1)

    def test_continuous_timestamps_do_not_keep_history_at_a_cut(self):
        result = assess(
            document(editBoundary=True, timestampsContinuous=True, carryHistory=False)
        )
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(any("reset history" in item for item in result["reasons"]))

    def test_second_evidence_id_is_preserved(self):
        evidence = "p108-fast-pan"
        result = assess(document(evidenceId=evidence))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            assess({})
        with self.assertRaises(ValueError):
            assess(document(depthSamples=[0.1, float("nan"), 0.4]))
        with self.assertRaises(ValueError):
            assess(document(depthSamples=[True, 0.2, 0.3]))
        with self.assertRaises(ValueError):
            assess(document(threshold=-0.1))
        with self.assertRaises(ValueError):
            assess(document(smoothed="true"))
