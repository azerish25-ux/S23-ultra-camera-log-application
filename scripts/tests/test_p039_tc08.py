"""TC-P039-08 throughput stage conflation."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p039_tc08", Path(__file__).resolve().parents[1] / "gates" / "p039_tc08.py"
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
        "acquisitionOnlyFps": "120",
        "savedSourceFps": "24",
        "savedRetained": True,
        "repeat": "increasing_duration",
        "advertiseAcquisitionAsSaved": False,
    }
    base.update(overrides)
    return base


class TcP03908(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P039-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_increasing_duration_keeps_stage_rates(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "retained_complete_path")
        self.assertNotEqual(result["decision"], "qualified")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("acquisitionOnly:120", result["preservedResults"])
        self.assertIn("savedSource:24", result["preservedResults"])
        self.assertIn("repeat:increasing_duration", result["preservedResults"])

    def test_storage_pressure_does_not_advertise_acquisition(self):
        result = evaluate(
            payload(savedSourceFps="0", savedRetained=False, repeat="storage_pressure")
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "stages_separated")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("acquisitionOnly:120", result["preservedResults"])
        self.assertIn("savedSource:0", result["preservedResults"])
        self.assertTrue(any("not retained" in item for item in result["openQuestions"]))

    def test_audio_selection_retained_path_is_not_qualified(self):
        result = evaluate(payload(repeat="audio_selection", savedSourceFps="12"))
        self.assertEqual(result["decision"], "retained_complete_path")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("savedSource:12", result["preservedResults"])
        self.assertIn("repeat:audio_selection", result["preservedResults"])

    def test_thermal_state_separates_a_failed_save(self):
        result = evaluate(
            payload(savedSourceFps="0", savedRetained=False, repeat="thermal_state")
        )
        self.assertEqual(result["decision"], "stages_separated")
        self.assertIn("repeat:thermal_state", result["preservedResults"])
        self.assertIn("acquisitionOnly:120", result["preservedResults"])

    def test_advertising_acquisition_as_saved_raw_is_rejected(self):
        result = evaluate(payload(advertiseAcquisitionAsSaved=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("acquisition-advertised-as-saved-raw", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("acquisitionOnly:120", result["preservedResults"])
        self.assertIn("savedSource:24", result["preservedResults"])


if __name__ == "__main__":
    unittest.main()
