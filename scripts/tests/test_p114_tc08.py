"""Tests for TC-P114-08."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p114_tc08",
    Path(__file__).resolve().parents[1] / "gates" / "p114_tc08.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
EFFECTS = ["stabilization", "virtual_focus", "motion_integration", "film_finishing"]


def payload(**overrides):
    base = {
        "evidenceId": "p114-evidence",
        "repeat": "scene cuts",
        "shutter_angle_degrees": 180.0,
        "fps": 24.0,
        "contains_estimated": False,
        "disclosed": True,
        "labelled_as_longer_sensor_exposure": False,
        "frames": [{"origin": "captured", "weight": 1.0}],
        "effects": list(EFFECTS),
        "individual_passes": {name: True for name in EFFECTS},
        "combined_checked": True,
        "doubled_edges": False,
        "unstable_masks": False,
        "cadence_changed": False,
        "shared_geometry": True,
    }
    base.update(overrides)
    return base


class TCP11408(unittest.TestCase):
    def assert_contract(self, result, evidence="p114-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P114-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])

    def test_combined_regression_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])

    def test_independent_passes_do_not_replace_the_combination(self):
        result = evaluate(payload(combined_checked=False, repeat="chunk resumes"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("independent-success-cannot-replace-combined-regression", result["rejectedClaims"])
        self.assertIn("p114-evidence", result["preservedResults"])

    def test_combined_artifacts_and_cadence_changes_are_rejected(self):
        edges = evaluate(payload(doubled_edges=True))
        self.assertIn("doubled-edges", edges["rejectedClaims"])
        masks = evaluate(payload(unstable_masks=True, repeat="low-confidence motion estimates"))
        self.assertIn("unstable-masks", masks["rejectedClaims"])
        cadence = evaluate(payload(cadence_changed=True))
        self.assertIn("unexplained-cadence-change", cadence["rejectedClaims"])
        geometry = evaluate(payload(shared_geometry=False))
        self.assertIn("shared-geometry-not-preserved", geometry["rejectedClaims"])

    def test_scope_rules_still_apply(self):
        hidden = evaluate(payload(
            frames=[{"origin": "estimated", "weight": 1.0}],
            contains_estimated=True,
            disclosed=False,
        ))
        self.assertIn("hidden-hallucination", hidden["rejectedClaims"])
        weights = evaluate(payload(frames=[{"origin": "captured", "weight": 0.1}]))
        self.assertIn("unnormalized-temporal-weights", weights["rejectedClaims"])
        labelled = evaluate(payload(labelled_as_longer_sensor_exposure=True))
        self.assertIn("labelled-as-longer-sensor-exposure", labelled["rejectedClaims"])
        missing = evaluate(payload(shutter_angle_degrees=None))
        self.assertIn("missing-shutter-angle", missing["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p114-chunk"
        result = evaluate(payload(evidenceId=evidence, repeat="chunk resumes"))
        self.assert_contract(result, evidence)

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(frames=[{"origin": "captured", "weight": -0.1}]))
        incomplete = evaluate(payload(effects=["stabilization"]))
        self.assertEqual(incomplete["decision"], "rejected")
        self.assertIn("independent-success-cannot-replace-combined-regression", incomplete["rejectedClaims"])
