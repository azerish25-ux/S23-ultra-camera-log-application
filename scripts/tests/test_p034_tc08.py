"""TC-P034-08 throughput stage conflation."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p034_tc08", Path(__file__).resolve().parents[1] / "gates" / "p034_tc08.py"
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
        "savedComplete": False,
        "discardedFrames": 10,
        "advertiseAcquisitionAsSaved": False,
        "durationS": 1,
        "storagePressure": False,
        "audioSelected": False,
        "thermal": "nominal",
    }
    base.update(overrides)
    return base


class TcP03408(unittest.TestCase):
    def assert_contract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P034-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("acquisition:120", result["preservedResults"])
        self.assertIn("saved:24", result["preservedResults"])
        self.assertNotIn("saved:120", result["preservedResults"])
        self.assertTrue(result["reasons"])

    def test_module_encodes_case_text(self):
        self.assertIn("acquisition-only", _MODULE.INTERVENTION)
        self.assertIn("separate stage rates", _MODULE.EXPECTED)
        self.assertIn("saved RAW recording performance", _MODULE.NEGATIVE)

    def test_failing_saved_source_keeps_rates_separate(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "stages_separated")
        self.assertEqual(result["openQuestions"], ["saved source not retained"])
        self.assertIn("discarded:10", result["preservedResults"])
        self.assertIn("acquisition stage 120", result["reasons"])
        self.assertIn("saved stage 24", result["reasons"])

    def test_retained_complete_path_is_not_qualification(self):
        result = evaluate(payload(savedComplete=True, discardedFrames=0))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "retained_complete")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("acquisition:120", result["preservedResults"])
        self.assertIn("saved:24", result["preservedResults"])
        self.assertIn("physical recording performance unverified", result["openQuestions"])

    def test_increasing_duration_still_separates_stages(self):
        result = evaluate(payload(durationS=30))
        self.assertEqual(result["decision"], "stages_separated")
        self.assertIn("duration:30", result["preservedResults"])
        self.assertIn("acquisition:120", result["preservedResults"])
        self.assertIn("saved:24", result["preservedResults"])

    def test_storage_pressure_does_not_conflate_rates(self):
        result = evaluate(payload(storagePressure=True, durationS=12))
        self.assertEqual(result["decision"], "stages_separated")
        self.assertIn("storage:True", result["preservedResults"])
        self.assertIn("saved:24", result["preservedResults"])
        self.assertNotIn("saved:120", result["preservedResults"])

    def test_audio_selection_is_preserved_separately(self):
        result = evaluate(payload(audioSelected=True))
        self.assertEqual(result["decision"], "stages_separated")
        self.assertIn("audio:True", result["preservedResults"])
        self.assertIn("acquisition:120", result["preservedResults"])

    def test_thermal_state_does_not_rewrite_saved_rate(self):
        result = evaluate(payload(thermal="hot", storagePressure=True))
        self.assertEqual(result["decision"], "stages_separated")
        self.assertIn("thermal:hot", result["preservedResults"])
        self.assertIn("saved:24", result["preservedResults"])
        self.assertEqual(result["openQuestions"], ["saved source not retained"])

    def test_negative_acquisition_advertised_as_saved_fails(self):
        result = evaluate(payload(advertiseAcquisitionAsSaved=True, discardedFrames=40))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "retained_complete", "stages_separated"})
        self.assertEqual(result["rejectedClaims"], ["acquisition-advertised-as-saved"])
        self.assertIn("acquisition:120", result["preservedResults"])
        self.assertIn("saved:24", result["preservedResults"])
        self.assertIn("discarded:40", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate(payload(acquisitionFps="0"))
        with self.assertRaises(ValueError):
            evaluate(payload(thermal="melting"))


if __name__ == "__main__":
    unittest.main()
