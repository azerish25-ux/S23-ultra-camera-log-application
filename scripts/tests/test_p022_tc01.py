"""TC-P022-01 stale callbacks do not resurrect recording."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p022_tc01", Path(__file__).resolve().parents[1] / "gates" / "p022_tc01.py"
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
_HASH = "cm-late-callback"


def payload(**overrides):
    base = {
        "currentOwner": "gen-2",
        "callbackGeneration": "gen-1",
        "stage": "before_first_sample",
        "resurrectsRecording": False,
        "attachesObsoleteSurface": False,
        "staleResources": ["surface-gen-1"],
        "currentResources": ["surface-gen-2"],
        "cleanMasterHash": _HASH,
    }
    base.update(overrides)
    return base


class TcP02201(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P022-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)

    def test_module_encodes_the_case_text(self):
        self.assertIn("previous camera", _MODULE.INTERVENTION)
        self.assertIn("stale operation", _MODULE.EXPECTED)
        self.assertIn("obsolete surface", _MODULE.NEGATIVE)
        self.assertIn("before_first_sample", _MODULE.STAGES)
        self.assertIn("after_camera_reopen", _MODULE.STAGES)

    def test_before_first_sample_releases_only_the_stale_surface(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "stale_ignored")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"], ["surface-gen-2", _HASH])
        self.assertNotIn("surface-gen-1", result["preservedResults"])
        self.assertTrue(any("surface-gen-1" in item for item in result["reasons"]))
        self.assertTrue(any("before_first_sample" in item for item in result["reasons"]))

    def test_during_stopping_also_ignores_the_stale_generation(self):
        result = evaluate(payload(stage="during_stopping", staleResources=["session-gen-1"]))
        self.assertContract(result)
        self.assertEqual(result["decision"], "stale_ignored")
        self.assertEqual(result["preservedResults"], ["surface-gen-2", _HASH])
        self.assertTrue(any("during_stopping" in item for item in result["reasons"]))
        self.assertTrue(any("session-gen-1" in item for item in result["reasons"]))

    def test_resurrection_after_activity_recreation_is_rejected(self):
        result = evaluate(
            payload(stage="after_activity_recreation", resurrectsRecording=True)
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "stale_ignored"})
        self.assertEqual(result["rejectedClaims"], ["resurrected-recording"])
        self.assertEqual(result["preservedResults"], ["surface-gen-2", _HASH])

    def test_obsolete_surface_after_camera_reopen_is_rejected(self):
        result = evaluate(
            payload(stage="after_camera_reopen", attachesObsoleteSurface=True)
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], ["obsolete-surface"])
        self.assertIn(_HASH, result["preservedResults"])
        self.assertIn("surface-gen-2", result["preservedResults"])

    def test_matching_owner_does_not_release_current_resources(self):
        result = evaluate(
            payload(callbackGeneration="gen-2", staleResources=[], stage="after_camera_reopen")
        )
        self.assertEqual(result["decision"], "owner_matched")
        self.assertEqual(result["preservedResults"], ["surface-gen-2", _HASH])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {**valid, "stage": "later"},
            {**valid, "resurrectsRecording": 1},
            {**valid, "staleResources": ["surface-gen-2"], "currentResources": ["surface-gen-2"]},
            {k: v for k, v in valid.items() if k != "cleanMasterHash"},
            {**valid, "extra": True},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
