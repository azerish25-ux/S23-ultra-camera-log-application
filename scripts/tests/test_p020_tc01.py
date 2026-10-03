"""TC-P020-01 host checks. Not a physical S23 probe."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p020_tc01", Path(__file__).resolve().parents[1] / "gates" / "p020_tc01.py"
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
_INVENTORY = _MODULE.WB_INVENTORY


def _contract(test, result):
    test.assertEqual(tuple(result), _KEYS)
    test.assertEqual(result["caseId"], "TC-P020-01")
    test.assertNotIn(result["decision"], {"qualified", "allowed"})
    test.assertIsInstance(result["reasons"], list)
    test.assertTrue(result["reasons"])
    test.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
    for key in ("rejectedClaims", "preservedResults", "openQuestions"):
        test.assertIsInstance(result[key], list)
        test.assertTrue(all(isinstance(item, str) for item in result[key]))


def _inventory(test, result):
    for item in _INVENTORY:
        test.assertIn(item, result["preservedResults"])


def payload(**overrides):
    base = {
        "callbackGeneration": 1,
        "currentOwner": 2,
        "phase": "before_first_sample",
        "resurrectsRecording": False,
        "attachesObsoleteSurface": False,
        "staleResources": ["surface-gen-1"],
        "currentResources": ["surface-gen-2"],
    }
    base.update(overrides)
    return base


class TcP02001(unittest.TestCase):
    def test_module_encodes_the_case_text(self):
        self.assertIn("previous camera", _MODULE.INTERVENTION)
        self.assertIn("stale operation", _MODULE.EXPECTED)
        self.assertIn("obsolete surface", _MODULE.NEGATIVE)
        self.assertIn("before_first_sample", _MODULE.REPEATS)
        self.assertIn("during_stopping", _MODULE.REPEATS)
        self.assertIn("after_activity_recreation", _MODULE.REPEATS)
        self.assertIn("after_camera_reopen", _MODULE.REPEATS)

    def test_before_first_sample_ignores_stale_callback(self):
        result = evaluate(payload())
        _contract(self, result)
        self.assertEqual(result["decision"], "ignored_stale")
        _inventory(self, result)
        self.assertIn("resource:surface-gen-2", result["preservedResults"])
        self.assertNotIn("resource:surface-gen-1", result["preservedResults"])
        self.assertTrue(any("before_first_sample" in item for item in result["reasons"]))
        self.assertTrue(any("surface-gen-1" in item for item in result["reasons"]))

    def test_during_stopping_also_ignores_the_stale_generation(self):
        result = evaluate(payload(phase="during_stopping", staleResources=["session-gen-1"]))
        _contract(self, result)
        self.assertEqual(result["decision"], "ignored_stale")
        _inventory(self, result)
        self.assertIn("resource:surface-gen-2", result["preservedResults"])
        self.assertTrue(any("during_stopping" in item for item in result["reasons"]))

    def test_resurrection_after_activity_recreation_is_rejected(self):
        result = evaluate(payload(phase="after_activity_recreation", resurrectsRecording=True))
        _contract(self, result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "ignored_stale"})
        self.assertIn("resurrect-recording", result["rejectedClaims"])
        _inventory(self, result)
        self.assertIn("resource:surface-gen-2", result["preservedResults"])

    def test_obsolete_surface_after_camera_reopen_is_rejected(self):
        result = evaluate(payload(phase="after_camera_reopen", attachesObsoleteSurface=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("obsolete-surface", result["rejectedClaims"])
        _inventory(self, result)

    def test_matching_owner_does_not_release_current_resources(self):
        result = evaluate(payload(callbackGeneration=2, staleResources=[], phase="after_camera_reopen"))
        self.assertEqual(result["decision"], "current_owner")
        _inventory(self, result)
        self.assertIn("resource:surface-gen-2", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {**valid, "phase": "later"},
            {**valid, "resurrectsRecording": 1},
            {**valid, "staleResources": ["surface-gen-2"], "currentResources": ["surface-gen-2"]},
            {k: v for k, v in valid.items() if k != "phase"},
            {**valid, "extra": True},
            {**valid, "callbackGeneration": 3},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
