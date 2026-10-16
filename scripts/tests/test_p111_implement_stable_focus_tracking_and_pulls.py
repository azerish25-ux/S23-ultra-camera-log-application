"""Host checks for P111. Not a physical S23 probe."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p111_implement_stable_focus_tracking_and_pulls",
    Path(__file__).resolve().parents[1] / "gates" / "p111_implement_stable_focus_tracking_and_pulls.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
assess = _MODULE.assess
fmt = _MODULE.fmt
interpolate_focus = _MODULE.interpolate_focus
pull_limiter = _MODULE.pull_limiter
describe_pull = _MODULE.describe_pull
max_one_frame_step = _MODULE.max_one_frame_step
MUTANT = _MODULE.MUTANT
ORACLE = _MODULE.ORACLE
BASE_REVISION = _MODULE.BASE_REVISION
PULL_LIMITER = _MODULE.PULL_LIMITER

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def document(**overrides):
    value = {
        "schemaVersion": 1,
        "phase": "P111",
        "implementationBaseRevision": BASE_REVISION,
        "evidenceId": "p111-crossing",
        "claim": "synthetic-host-fixture",
        "applyMutant": False,
        "frameMs": 40,
        "maxDistancePerFrame": 0.25,
        "confidenceThreshold": 0.5,
        "labelledSmooth": True,
        "pull": [
            {"t_ms": 0, "focus_distance": 1.0},
            {"t_ms": 40, "focus_distance": 1.25},
            {"t_ms": 80, "focus_distance": 1.5},
        ],
        "query": {
            "t_ms": 20,
            "reportedFocus": 1.125,
            "reportedState": "interpolated",
            "claimsInterpolationBeyondKeys": False,
        },
        "tracking": [
            {
                "t_ms": 0,
                "confidence": 0.9,
                "proposedFocus": 1.0,
                "appliedFocus": 1.0,
                "appliedState": "tracking",
                "identity": "subject-a",
                "selectedIdentity": "subject-a",
                "nearestFaceFocus": 1.0,
            },
            {
                "t_ms": 40,
                "confidence": 0.25,
                "proposedFocus": 0.5,
                "appliedFocus": 1.0,
                "appliedState": "held",
                "identity": "subject-a",
                "selectedIdentity": "subject-a",
                "nearestFaceFocus": 0.5,
            },
            {
                "t_ms": 80,
                "confidence": 0.8,
                "proposedFocus": 1.25,
                "appliedFocus": 1.25,
                "appliedState": "tracking",
                "identity": "subject-a",
                "selectedIdentity": "subject-a",
                "nearestFaceFocus": 0.5,
            },
        ],
    }
    value.update(overrides)
    return value


class P111Tests(unittest.TestCase):
    def assert_contract(self, result, evidence="p111-crossing"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "P111")
        self.assertIn(result["decision"], {"recorded", "rejected"})
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("duration_ms:80", result["preservedResults"])
        self.assertIn(f"start_distance:{fmt(1.0)}", result["preservedResults"])
        self.assertIn(f"end_distance:{fmt(1.5)}", result["preservedResults"])
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))
        self.assertTrue(any("not run" in item for item in result["openQuestions"]))
        self.assertIn(ORACLE, " ".join(result["reasons"]))
        self.assertIn(PULL_LIMITER, " ".join(result["reasons"]))

    def test_smooth_pull_is_recorded_not_qualified(self):
        result = assess(document())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(any("state held" in item for item in result["reasons"]))
        self.assertTrue(any(item.startswith("pull_recipe:") for item in result["preservedResults"]))
        self.assertTrue(any("held" in item for item in result["preservedResults"]))

    def test_authored_fixture_matches_the_gate(self):
        path = Path(__file__).resolve().parents[2] / "docs" / "P111_IMPLEMENT_STABLE_FOCUS_TRACKING_AND_PULLS.json"
        result = assess(json.loads(path.read_text(encoding="utf-8")))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")

    def test_mutant_is_rejected_and_evidence_remains(self):
        result = assess(document(applyMutant=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(MUTANT, result["rejectedClaims"])

    def test_one_frame_jump_labelled_smooth_is_rejected(self):
        pull = [
            {"t_ms": 0, "focus_distance": 1.0},
            {"t_ms": 40, "focus_distance": 2.0},
            {"t_ms": 80, "focus_distance": 2.25},
        ]
        query = {
            "t_ms": 20,
            "reportedFocus": 1.5,
            "reportedState": "interpolated",
            "claimsInterpolationBeyondKeys": False,
        }
        result = assess(document(pull=pull, query=query))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("one-frame-jump-exceeds-pull-limiter", result["rejectedClaims"])
        self.assertIn("p111-crossing", result["preservedResults"])
        self.assertIn("duration_ms:80", result["preservedResults"])
        self.assertIn(f"start_distance:{fmt(1.0)}", result["preservedResults"])
        self.assertIn(f"end_distance:{fmt(2.25)}", result["preservedResults"])
        self.assertTrue(any("smooth pull" in item for item in result["reasons"]))

    def test_unlabelled_jump_is_not_called_a_smooth_pull(self):
        pull = [
            {"t_ms": 0, "focus_distance": 1.0},
            {"t_ms": 40, "focus_distance": 2.0},
            {"t_ms": 80, "focus_distance": 2.25},
        ]
        query = {
            "t_ms": 20,
            "reportedFocus": 1.5,
            "reportedState": "interpolated",
            "claimsInterpolationBeyondKeys": False,
        }
        result = assess(document(pull=pull, query=query, labelledSmooth=False))
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(any("not labelled as a smooth pull" in item for item in result["reasons"]))

    def test_claiming_interpolation_past_the_last_key_is_rejected(self):
        query = {
            "t_ms": 120,
            "reportedFocus": 1.5,
            "reportedState": "interpolated",
            "claimsInterpolationBeyondKeys": True,
        }
        result = assess(document(query=query))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("claimed-interpolation-beyond-keys", result["rejectedClaims"])
        self.assertIn("clamp-without-held", result["rejectedClaims"])
        self.assertIn("p111-crossing", result["preservedResults"])
        self.assertTrue(any("not extrapolated" in item for item in result["reasons"]))

    def test_hold_past_the_last_key_is_recorded(self):
        query = {
            "t_ms": 120,
            "reportedFocus": 1.5,
            "reportedState": "held",
            "claimsInterpolationBeyondKeys": False,
        }
        result = assess(document(query=query))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertTrue(any("state=held" in item for item in result["reasons"]))

    def test_low_confidence_jump_is_rejected(self):
        tracking = [
            {
                "t_ms": 0,
                "confidence": 0.9,
                "proposedFocus": 1.0,
                "appliedFocus": 1.0,
                "appliedState": "tracking",
                "identity": "subject-a",
                "selectedIdentity": "subject-a",
                "nearestFaceFocus": 1.0,
            },
            {
                "t_ms": 40,
                "confidence": 0.2,
                "proposedFocus": 0.5,
                "appliedFocus": 0.5,
                "appliedState": "tracking",
                "identity": "subject-a",
                "selectedIdentity": "subject-a",
                "nearestFaceFocus": 0.75,
            },
        ]
        result = assess(document(tracking=tracking))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("jump-on-low-confidence", result["rejectedClaims"])
        self.assertIn("tracking-loss-not-held", result["rejectedClaims"])
        self.assertNotIn("nearest-face-independently-every-frame", result["rejectedClaims"])
        self.assertIn("duration_ms:80", result["preservedResults"])

    def test_nearest_face_every_frame_is_the_mutant(self):
        tracking = [
            {
                "t_ms": 0,
                "confidence": 0.9,
                "proposedFocus": 2.0,
                "appliedFocus": 1.0,
                "appliedState": "tracking",
                "identity": "subject-a",
                "selectedIdentity": "subject-a",
                "nearestFaceFocus": 1.0,
            },
            {
                "t_ms": 40,
                "confidence": 0.2,
                "proposedFocus": 2.0,
                "appliedFocus": 0.5,
                "appliedState": "tracking",
                "identity": "subject-b",
                "selectedIdentity": "subject-a",
                "nearestFaceFocus": 0.5,
            },
        ]
        result = assess(document(tracking=tracking))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(MUTANT, result["rejectedClaims"])
        self.assertIn("jump-on-low-confidence", result["rejectedClaims"])

    def test_pull_limiter_clamps_one_frame_and_keeps_the_sign(self):
        self.assertEqual(pull_limiter(1.0, 1.25, 0.25), 1.25)
        self.assertEqual(pull_limiter(1.0, 2.0, 0.25), 1.25)
        self.assertEqual(pull_limiter(2.0, 1.0, 0.25), 1.75)
        self.assertEqual(PULL_LIMITER, "max_distance_per_frame")

    def test_interpolation_is_linear_and_does_not_extrapolate(self):
        keys = [
            {"t_ms": 0, "focus_distance": 1.0},
            {"t_ms": 40, "focus_distance": 1.25},
        ]
        midpoint = interpolate_focus(keys, 20)
        quarter = interpolate_focus(keys, 10)
        self.assertEqual(midpoint["state"], "interpolated")
        self.assertEqual(midpoint["focus_distance"], 1.125)
        self.assertEqual(quarter["focus_distance"], 1.0625)
        self.assertEqual(interpolate_focus(keys, 0)["state"], "key")
        held = interpolate_focus(keys, 80)
        self.assertEqual(held["state"], "held")
        self.assertEqual(held["focus_distance"], 1.25)
        self.assertNotEqual(held["focus_distance"], 1.5)
        before = interpolate_focus(keys, 0) if False else interpolate_focus(
            [{"t_ms": 40, "focus_distance": 1.0}, {"t_ms": 80, "focus_distance": 2.0}],
            0,
        )
        self.assertEqual(before["state"], "held")
        self.assertEqual(before["focus_distance"], 1.0)
        described = describe_pull(keys)
        self.assertEqual(described["duration_ms"], 40)
        self.assertEqual(described["start_distance"], 1.0)
        self.assertEqual(described["end_distance"], 1.25)
        self.assertEqual(max_one_frame_step(keys, 40), 0.25)

    def test_invalid_document_raises(self):
        with self.assertRaises(ValueError):
            assess({})
        with self.assertRaises(ValueError):
            assess(document(pull=[
                {"t_ms": 0, "focus_distance": 1.0},
                {"t_ms": 40, "focus_distance": float("nan")},
            ]))
        with self.assertRaises(ValueError):
            assess(document(evidenceId=" padded "))
        with self.assertRaises(ValueError):
            pull_limiter(1.0, 2.0, 0.0)
        with self.assertRaises(ValueError):
            interpolate_focus([{"t_ms": 0, "focus_distance": 1.0}], 0)
