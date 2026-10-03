"""TC-P038-08 acquisition speed is not saved RAW performance."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p038_tc08", Path(__file__).resolve().parents[1] / "gates" / "p038_tc08.py"
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
        "acquisitionFps": "120",
        "savedFps": "24",
        "savedComplete": True,
        "discardedFrames": 40,
        "advertiseAcquisitionAsSaved": False,
        "durationS": 5,
        "storagePressure": False,
        "audioSelected": False,
        "thermalState": "nominal",
    }
    base.update(overrides)
    return base


class TcP03808(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P038-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn("acquisitionFps:120", result["preservedResults"])
        self.assertTrue(any(item.startswith("savedFps:") for item in result["preservedResults"]))

    def test_retained_complete_path_is_not_qualified(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "retained_path")
        self.assertNotEqual(result["decision"], "qualified")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("savedFps:24", result["preservedResults"])
        self.assertIn("discardedFrames:40", result["preservedResults"])
        self.assertTrue(any("separately" in item for item in result["reasons"]))
        self.assertTrue(any("not a qualified" in item for item in result["reasons"]))

    def test_longer_duration_and_storage_pressure_keep_separate_rates(self):
        result = evaluate(payload(durationS=60, storagePressure=True, savedFps="12"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "retained_path")
        self.assertIn("durationS:60", result["preservedResults"])
        self.assertIn("savedFps:12", result["preservedResults"])
        self.assertIn("acquisitionFps:120", result["preservedResults"])
        self.assertIn("storage pressure recorded separately", result["openQuestions"])

    def test_audio_selection_and_thermal_state_do_not_merge_stages(self):
        result = evaluate(payload(audioSelected=True, thermalState="severe", durationS=30))
        self.assertEqual(result["decision"], "retained_path")
        self.assertIn("audio:true", result["preservedResults"])
        self.assertIn("thermal:severe", result["preservedResults"])
        self.assertIn("thermal:severe", result["openQuestions"])
        self.assertIn("acquisitionFps:120", result["preservedResults"])
        self.assertIn("savedFps:24", result["preservedResults"])

    def test_failing_saved_source_does_not_promote_acquisition(self):
        result = evaluate(payload(savedComplete=False, savedFps="1"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertIn("saved source incomplete", result["openQuestions"])
        self.assertIn("acquisitionFps:120", result["preservedResults"])
        self.assertIn("savedFps:1", result["preservedResults"])
        self.assertTrue(any("not a saved RAW result" in item for item in result["reasons"]))

    def test_advertising_acquisition_as_saved_raw_fails(self):
        result = evaluate(payload(advertiseAcquisitionAsSaved=True, discardedFrames=90))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["acquisition-advertised-as-saved"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("discardedFrames:90", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "retained_path"})
        joined = " ".join(result["preservedResults"])
        self.assertIn("acquisitionFps:120", joined)
        self.assertNotIn("savedFps:120", joined)

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate(payload(acquisitionFps="120.0"))
        with self.assertRaises(ValueError):
            evaluate(payload(thermalState="meltdown"))


if __name__ == "__main__":
    unittest.main()
