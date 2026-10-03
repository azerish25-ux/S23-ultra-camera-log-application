"""TC-P037-08 throughput stage conflation."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p037_tc08", Path(__file__).resolve().parents[1] / "gates" / "p037_tc08.py"
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


class TcP03708(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P037-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_increasing_duration_keeps_separate_rates(self):
        result = evaluate(payload(repeat="increasing_duration", acquisitionOnlyFps="240"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "retained_complete_path")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("acquisition-only rate 240", result["reasons"])
        self.assertIn("saved-source rate 24", result["reasons"])
        self.assertNotIn("saved-source rate 240", result["reasons"])
        self.assertIn("acquisitionOnly:240", result["preservedResults"])
        self.assertIn("savedSource:24", result["preservedResults"])

    def test_storage_pressure_does_not_promote_acquisition_speed(self):
        result = evaluate(
            payload(
                repeat="storage_pressure",
                savedRetained=False,
                savedSourceFps="0",
                acquisitionOnlyFps="120",
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "stages_separated")
        self.assertNotEqual(result["decision"], "retained_complete_path")
        self.assertIn("acquisitionOnly:120", result["preservedResults"])
        self.assertIn("savedSource:0", result["preservedResults"])
        self.assertTrue(any("not saved RAW performance" in item for item in result["openQuestions"]))

    def test_audio_selection_reports_the_retained_path_only(self):
        result = evaluate(payload(repeat="audio_selection", acquisitionOnlyFps="60", savedSourceFps="24"))
        self.assertEqual(result["decision"], "retained_complete_path")
        self.assertIn("repeat:audio_selection", result["preservedResults"])
        self.assertIn("acquisition-only rate 60", result["reasons"])
        self.assertIn("saved-source rate 24", result["reasons"])

    def test_thermal_state_keeps_a_failed_saved_path_separate(self):
        result = evaluate(
            payload(
                repeat="thermal_state",
                savedRetained=False,
                savedSourceFps="12.5",
                acquisitionOnlyFps="120",
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "stages_separated")
        self.assertIn("savedSource:12.5", result["preservedResults"])
        self.assertIn("acquisitionOnly:120", result["preservedResults"])

    def test_advertising_acquisition_as_saved_raw_fails(self):
        result = evaluate(payload(advertiseAcquisitionAsSaved=True, acquisitionOnlyFps="240"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "retained_complete_path"})
        self.assertIn("acquisition-advertised-as-saved-raw", result["rejectedClaims"])
        self.assertIn("acquisitionOnly:240", result["preservedResults"])
        self.assertIn("savedSource:24", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "acquisitionOnlyFps": "0"},
            {**valid, "savedSourceFps": "0", "savedRetained": True},
            {**valid, "repeat": "forever"},
            {**valid, "advertiseAcquisitionAsSaved": "yes"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
