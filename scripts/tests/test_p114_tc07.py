"""Tests for TC-P114-07."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p114_tc07",
    Path(__file__).resolve().parents[1] / "gates" / "p114_tc07.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p114-evidence",
        "repeat": "thermal advice",
        "shutter_angle_degrees": 180.0,
        "fps": 24.0,
        "contains_estimated": False,
        "disclosed": True,
        "labelled_as_longer_sensor_exposure": False,
        "frames": [{"origin": "captured", "weight": 1.0}],
        "manual_exposure": True,
        "manual_focus": True,
        "advice_enabled": True,
        "clipping_warnings_disabled": False,
        "shutter_changed": False,
    }
    base.update(overrides)
    return base


class TCP11407(unittest.TestCase):
    def assert_contract(self, result, evidence="p114-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P114-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])

    def test_warnings_without_setting_changes_are_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(any("clipping warnings unchanged" in item for item in result["reasons"]))

    def test_silent_shutter_or_clipping_change_is_rejected(self):
        shutter = evaluate(payload(shutter_changed=True, repeat="focus warnings"))
        self.assert_contract(shutter)
        self.assertEqual(shutter["decision"], "rejected")
        self.assertIn("silent-clipping-warning-disable-or-shutter-change", shutter["rejectedClaims"])
        clipping = evaluate(payload(clipping_warnings_disabled=True, repeat="incompatible virtual-lens framing"))
        self.assertIn("silent-clipping-warning-disable-or-shutter-change", clipping["rejectedClaims"])
        self.assertIn("p114-evidence", clipping["preservedResults"])

    def test_scope_rules_still_apply(self):
        hidden = evaluate(payload(
            frames=[{"origin": "estimated", "weight": 1.0}],
            contains_estimated=False,
            disclosed=True,
        ))
        self.assertIn("estimated-origin-requires-contains-estimated", hidden["rejectedClaims"])
        undisclosed = evaluate(payload(
            frames=[{"origin": "estimated", "weight": 1.0}],
            contains_estimated=True,
            disclosed=False,
        ))
        self.assertIn("hidden-hallucination", undisclosed["rejectedClaims"])
        labelled = evaluate(payload(labelled_as_longer_sensor_exposure=True))
        self.assertIn("labelled-as-longer-sensor-exposure", labelled["rejectedClaims"])
        missing = evaluate(payload(fps=None))
        self.assertIn("missing-fps", missing["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p114-focus"
        result = evaluate(payload(evidenceId=evidence, repeat="focus warnings"))
        self.assert_contract(result, evidence)

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(manual_exposure="yes"))
