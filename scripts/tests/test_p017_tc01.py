"""TC-P017-01 late callback generation."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p017_tc01", Path(__file__).resolve().parents[1] / "gates" / "p017_tc01.py"
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


def payload(**overrides):
    base = {
        "stage": "before_first_sample",
        "callbackGeneration": 1,
        "currentGeneration": 2,
        "resurrectRecording": False,
        "attachObsoleteSurface": False,
        "staleResourceIds": ["surface-prev", "session-stale"],
        "currentResourceIds": ["surface-active", "session-active"],
        "activePreview": "surface-active",
    }
    base.update(overrides)
    return base


class TcP01701(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P017-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)

    def test_constants_encode_the_case(self):
        self.assertIn("previous camera or recording generation", _MODULE.INTERVENTION)
        self.assertIn("stale operation", _MODULE.EXPECTED)
        self.assertIn("resurrects recording", _MODULE.NEGATIVE)
        self.assertEqual(
            _MODULE.STAGES,
            (
                "before_first_sample",
                "during_stopping",
                "after_activity_recreation",
                "after_camera_reopen",
            ),
        )

    def test_before_first_sample_ignores_stale_callback(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "stale_ignored")
        self.assertEqual(result["preservedResults"], ["surface-active", "session-active"])
        self.assertIn("surface-active", result["preservedResults"])
        self.assertNotIn("surface-prev", result["preservedResults"])
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(any("before_first_sample" in item for item in result["reasons"]))
        self.assertTrue(any("ignore stale state mutation" in item for item in result["reasons"]))
        self.assertTrue(any("surface-prev" in item for item in result["reasons"]))

    def test_during_stopping_keeps_current_owner(self):
        result = evaluate(payload(stage="during_stopping", staleResourceIds=["image-stale"]))
        self.assertContract(result)
        self.assertEqual(result["decision"], "stale_ignored")
        self.assertEqual(result["preservedResults"], ["surface-active", "session-active"])
        self.assertNotIn("image-stale", result["preservedResults"])
        self.assertTrue(any("during_stopping" in item for item in result["reasons"]))

    def test_after_activity_recreation_does_not_attach_obsolete_surface(self):
        result = evaluate(payload(stage="after_activity_recreation"))
        self.assertEqual(result["decision"], "stale_ignored")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("surface-active", result["preservedResults"])
        self.assertNotIn("session-stale", result["preservedResults"])

    def test_after_camera_reopen_releases_only_stale_ids(self):
        result = evaluate(
            payload(
                stage="after_camera_reopen",
                callbackGeneration=3,
                currentGeneration=4,
                staleResourceIds=["session-3"],
                currentResourceIds=["camera-4", "surface-4"],
                activePreview="surface-4",
            )
        )
        self.assertEqual(result["decision"], "stale_ignored")
        self.assertEqual(result["preservedResults"], ["camera-4", "surface-4"])
        self.assertTrue(any("session-3" in item for item in result["reasons"]))
        self.assertNotIn("session-3", result["preservedResults"])

    def test_resurrect_recording_is_rejected_and_inventory_remains(self):
        result = evaluate(payload(stage="during_stopping", resurrectRecording=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], ["resurrect-recording"])
        self.assertEqual(result["preservedResults"], ["surface-active", "session-active"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_obsolete_surface_attach_is_rejected(self):
        result = evaluate(payload(stage="after_activity_recreation", attachObsoleteSurface=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["attach-obsolete-surface"])
        self.assertIn("surface-active", result["preservedResults"])
        self.assertNotIn("surface-prev", result["preservedResults"])

    def test_both_negative_controls_are_rejected_together(self):
        result = evaluate(payload(resurrectRecording=True, attachObsoleteSurface=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(
            result["rejectedClaims"],
            ["resurrect-recording", "attach-obsolete-surface"],
        )
        self.assertEqual(result["preservedResults"], ["surface-active", "session-active"])

    def test_current_generation_is_not_qualified(self):
        result = evaluate(payload(callbackGeneration=2, currentGeneration=2, staleResourceIds=[]))
        self.assertEqual(result["decision"], "current_owner")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["preservedResults"], ["surface-active", "session-active"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "stage"},
            {**valid, "extra": True},
            {**valid, "stage": "after_stop"},
            {**valid, "callbackGeneration": True},
            {**valid, "callbackGeneration": 0},
            {**valid, "resurrectRecording": "true"},
            {**valid, "staleResourceIds": ["surface-active"]},
            {**valid, "activePreview": "surface-prev"},
            {**valid, "currentResourceIds": []},
            {**valid, "staleResourceIds": ["a", "a"]},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
