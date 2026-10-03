"""TC-P021-01 late callback generation."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p021_tc01", Path(__file__).resolve().parents[1] / "gates" / "p021_tc01.py"
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_FOCUS = _MODULE.FOCUS_INVENTORY


def payload(**overrides):
    base = {
        "callbackGeneration": 1,
        "currentOwner": 2,
        "phase": "before_first_sample",
        "resurrectsRecording": False,
        "attachesObsoleteSurface": False,
        "staleResources": ["stale-surface"],
        "currentResources": ["current-surface"],
    }
    base.update(overrides)
    return base


class TcP02101(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P021-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
        for token in _FOCUS:
            self.assertIn(token, result["preservedResults"])

    def test_module_encodes_intervention_expected_and_negative(self):
        self.assertIn("previous camera or recording generation", _MODULE.INTERVENTION)
        self.assertIn("Ignore stale state mutation", _MODULE.EXPECTED)
        self.assertIn("resurrects recording", _MODULE.NEGATIVE)
        self.assertIn("before_first_sample", _MODULE.REPEATS)
        self.assertIn("during_stopping", _MODULE.REPEATS)
        self.assertIn("after_activity_recreation", _MODULE.REPEATS)
        self.assertIn("after_camera_reopen", _MODULE.REPEATS)

    def test_repeat_before_first_sample_ignores_stale_callback(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "ignored_stale")
        self.assertIn("resource:current-surface", result["preservedResults"])
        self.assertNotIn("resource:stale-surface", result["preservedResults"])
        self.assertIn("stale-generation:1", result["rejectedClaims"])
        self.assertTrue(any("before_first_sample" in item for item in result["reasons"]))
        self.assertTrue(any("stale-surface" in item for item in result["reasons"]))

    def test_repeat_during_stopping_ignores_stale_callback(self):
        result = evaluate(payload(phase="during_stopping", callbackGeneration=0, currentOwner=3))
        self.assertContract(result)
        self.assertEqual(result["decision"], "ignored_stale")
        self.assertTrue(any("during_stopping" in item for item in result["reasons"]))
        self.assertIn("physical.distance:unknown", result["preservedResults"])

    def test_repeat_after_activity_recreation_and_camera_reopen(self):
        for phase in ("after_activity_recreation", "after_camera_reopen"):
            result = evaluate(payload(phase=phase, currentResources=["live-session"]))
            self.assertContract(result)
            self.assertEqual(result["decision"], "ignored_stale")
            self.assertIn("resource:live-session", result["preservedResults"])
            self.assertTrue(any(phase in item for item in result["reasons"]))

    def test_negative_resurrect_recording_is_rejected(self):
        result = evaluate(payload(resurrectsRecording=True, phase="during_stopping"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("resurrect-recording", result["rejectedClaims"])
        self.assertIn("resource:current-surface", result["preservedResults"])
        self.assertNotIn("resource:stale-surface", result["preservedResults"])
        self.assertIn("virtual.subject:face", result["preservedResults"])

    def test_negative_obsolete_surface_is_rejected(self):
        result = evaluate(
            payload(attachesObsoleteSurface=True, phase="after_camera_reopen", resurrectsRecording=True)
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("obsolete-surface", result["rejectedClaims"])
        self.assertIn("resurrect-recording", result["rejectedClaims"])
        self.assertIn("physical.subject:nearby_foreground", result["preservedResults"])

    def test_current_owner_callback_is_not_stale(self):
        result = evaluate(payload(callbackGeneration=2, currentOwner=2, staleResources=[]))
        self.assertEqual(result["decision"], "current_owner")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("resource:current-surface", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "callbackGeneration": 3},
            {**valid, "phase": "later"},
            {**valid, "resurrectsRecording": "true"},
            {**valid, "staleResources": ["current-surface"]},
            {**valid, "extra": True},
            {k: v for k, v in valid.items() if k != "phase"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
