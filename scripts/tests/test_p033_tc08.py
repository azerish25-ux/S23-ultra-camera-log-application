"""TC-P033-08 throughput stage conflation."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p033_tc08", Path(__file__).resolve().parents[1] / "gates" / "p033_tc08.py"
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
_FORBIDDEN = {"qualified", "allowed"}


def payload(**overrides):
    base = {
        "acquisitionFps": "120",
        "savedFps": "12",
        "savedFailed": False,
        "discardedFrames": 4,
        "advertiseAcquisitionAsSaved": False,
        "duration": "short",
        "storagePressure": False,
        "audioSelected": False,
        "thermal": "nominal",
        "retainedComplete": True,
        "inventory": ["acq-report", "saved-report"],
    }
    base.update(overrides)
    return base


class TcP03308(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P033-08")
        self.assertNotIn(result["decision"], _FORBIDDEN)
        self.assertTrue(result["reasons"])
        self.assertIn("acquisition:120", result["preservedResults"])
        self.assertIn("saved:12", result["preservedResults"])
        self.assertIn("acq-report", result["preservedResults"])
        self.assertIn("saved-report", result["preservedResults"])

    def test_repeat_increasing_duration_keeps_rates_separate(self):
        result = evaluate(payload(duration="increasing", discardedFrames=0))
        self.assertContract(result)
        self.assertEqual(result["decision"], "retained_complete")
        self.assertNotIn(result["decision"], _FORBIDDEN)
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("duration:increasing", result["preservedResults"])
        self.assertTrue(any("increasing duration" in item for item in result["openQuestions"]))
        self.assertTrue(any("not acquisition speed" in item for item in result["reasons"]))

    def test_repeat_storage_pressure_stays_on_the_saved_stage(self):
        result = evaluate(
            payload(storagePressure=True, savedFailed=True, retainedComplete=False, duration="increasing")
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "stages_separated")
        self.assertNotIn(result["decision"], _FORBIDDEN | {"retained_complete"})
        self.assertIn("saved-path-incomplete", result["rejectedClaims"])
        self.assertNotIn("acquisition-advertised-as-saved", result["rejectedClaims"])
        self.assertIn("storage:pressure", result["preservedResults"])
        self.assertIn("discarded:4", result["preservedResults"])
        self.assertTrue(any("storage pressure" in item for item in result["openQuestions"]))

    def test_repeat_audio_selection_does_not_merge_rates(self):
        result = evaluate(payload(audioSelected=True, discardedFrames=0))
        self.assertContract(result)
        self.assertEqual(result["decision"], "retained_complete")
        self.assertNotIn(result["decision"], _FORBIDDEN)
        self.assertIn("audio:selected", result["preservedResults"])
        self.assertTrue(any("audio selection" in item for item in result["openQuestions"]))

    def test_repeat_thermal_state_does_not_upgrade_acquisition(self):
        result = evaluate(
            payload(thermal="severe", savedFailed=True, retainedComplete=False, discardedFrames=10)
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "stages_separated")
        self.assertNotIn(result["decision"], _FORBIDDEN)
        self.assertIn("thermal:severe", result["preservedResults"])
        self.assertIn("discarded:10", result["preservedResults"])
        self.assertIn("acquisition:120", result["preservedResults"])
        self.assertIn("saved:12", result["preservedResults"])
        self.assertTrue(any("thermal state" in item for item in result["openQuestions"]))

    def test_negative_advertise_acquisition_as_saved(self):
        result = evaluate(
            payload(advertiseAcquisitionAsSaved=True, discardedFrames=30, duration="increasing")
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], _FORBIDDEN | {"retained_complete", "stages_separated"})
        self.assertEqual(result["rejectedClaims"], ["acquisition-advertised-as-saved"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("acquisition:120", result["preservedResults"])
        self.assertIn("saved:12", result["preservedResults"])
        self.assertIn("discarded:30", result["preservedResults"])
        self.assertIn("acq-report", result["preservedResults"])

    def test_failing_saved_source_keeps_both_rates(self):
        result = evaluate(payload(savedFailed=True, retainedComplete=False))
        self.assertContract(result)
        self.assertEqual(result["decision"], "stages_separated")
        self.assertIn("saved-path-incomplete", result["rejectedClaims"])
        self.assertIn("acquisition:120", result["preservedResults"])
        self.assertIn("saved:12", result["preservedResults"])
        self.assertNotIn(result["decision"], _FORBIDDEN)
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "acquisitionFps": "120.0"},
            {**valid, "savedFps": "0"},
            {**valid, "savedFailed": True, "retainedComplete": True},
            {**valid, "discardedFrames": -1},
            {**valid, "duration": "long"},
            {**valid, "thermal": "hot"},
            {**valid, "advertiseAcquisitionAsSaved": "yes"},
            {**valid, "inventory": ["acq-report", "acq-report"]},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
