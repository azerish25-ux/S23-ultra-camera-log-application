"""TC-P019-01 late callback generation."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p019_tc01", Path(__file__).resolve().parents[1] / "gates" / "p019_tc01.py"
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
        "moment": "before_first_sample",
        "currentGeneration": 2,
        "currentOwner": "session-b",
        "recording": False,
        "attachedSurface": "surface-new",
        "currentResources": ["camera-b", "surface-new"],
        "callbackGeneration": 1,
        "callbackOwner": "session-a",
        "callbackType": "first_video_sample",
        "resurrectRecording": False,
        "attachObsoleteSurface": False,
        "staleResources": ["surface-old"],
    }
    base.update(overrides)
    return base


class TcP01901(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P019-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)

    def test_module_encodes_the_case_contract(self):
        self.assertEqual(
            _MODULE.INTERVENTION,
            "Deliver a successful callback from a previous camera or recording generation "
            "after the current owner has changed.",
        )
        self.assertEqual(
            _MODULE.EXPECTED,
            "Ignore stale state mutation and release only resources owned by the stale operation.",
        )
        self.assertEqual(
            _MODULE.NEGATIVE,
            "A delayed callback that resurrects recording or attaches an obsolete surface must fail.",
        )
        self.assertIn("before first sample", _MODULE.REPEAT)
        self.assertIn("during stopping", _MODULE.REPEAT)

    def test_before_first_sample_ignores_stale_callback(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "stale_ignored")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("resource:camera-b", result["preservedResults"])
        self.assertIn("resource:surface-new", result["preservedResults"])
        self.assertNotIn("resource:surface-old", result["preservedResults"])
        self.assertIn("surface:surface-new", result["preservedResults"])
        self.assertIn("recording:false", result["preservedResults"])
        self.assertIn("state:starting", result["preservedResults"])
        self.assertIn("owner:session-b", result["preservedResults"])
        self.assertTrue(any("surface-old" in item for item in result["reasons"]))

    def test_during_stopping_ignores_stale_callback(self):
        result = evaluate(
            payload(moment="during_stopping", callbackType="audio_format", staleResources=["mic-old"])
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "stale_ignored")
        self.assertIn("state:stopping", result["preservedResults"])
        self.assertIn("recording:false", result["preservedResults"])
        self.assertIn("resource:camera-b", result["preservedResults"])
        self.assertTrue(any("mic-old" in item for item in result["reasons"]))
        self.assertNotIn("resource:mic-old", result["preservedResults"])

    def test_after_activity_recreation_and_camera_reopen(self):
        for moment, state in (
            ("after_activity_recreation", "preview"),
            ("after_camera_reopen", "opening"),
        ):
            result = evaluate(payload(moment=moment, callbackType="success"))
            with self.subTest(moment=moment):
                self.assertEqual(result["decision"], "stale_ignored")
                self.assertIn("state:" + state, result["preservedResults"])
                self.assertIn("recording:false", result["preservedResults"])
                self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_negative_resurrection_and_obsolete_surface_are_rejected(self):
        result = evaluate(
            payload(
                moment="during_stopping",
                callbackType="surface_attach",
                resurrectRecording=True,
                attachObsoleteSurface=True,
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], ["resurrect-recording", "obsolete-surface"])
        self.assertIn("recording:false", result["preservedResults"])
        self.assertIn("surface:surface-new", result["preservedResults"])
        self.assertIn("resource:camera-b", result["preservedResults"])

    def test_current_generation_without_the_negative_is_not_stale(self):
        result = evaluate(
            payload(
                callbackGeneration=2,
                callbackOwner="session-b",
                staleResources=[],
                callbackType="success",
            )
        )
        self.assertEqual(result["decision"], "not_stale")
        self.assertIn("resource:surface-new", result["preservedResults"])
        self.assertIn("recording:false", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "moment"},
            {**valid, "extra": True},
            {**valid, "moment": "after_stop"},
            {**valid, "recording": "false"},
            {**valid, "recording": True},
            {**valid, "currentGeneration": 0},
            {**valid, "currentResources": []},
            {**valid, "currentResources": ["surface-old"], "staleResources": ["surface-old"]},
            {**valid, "callbackType": "record"},
            {**valid, "attachedSurface": ""},
            {**valid, "resurrectRecording": 1},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
