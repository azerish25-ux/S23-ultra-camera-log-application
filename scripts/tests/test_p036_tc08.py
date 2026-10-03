"""TC-P036-08 throughput stage conflation."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p036_tc08", Path(__file__).resolve().parents[1] / "gates" / "p036_tc08.py"
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
        "acquisitionRate": "120",
        "savedRate": "24",
        "savedComplete": True,
        "savedRetained": True,
        "framesDiscarded": True,
        "advertiseAcquisitionAsSaved": False,
        "duration": "baseline",
        "storagePressure": False,
        "audioSelection": "off",
        "thermalState": "nominal",
    }
    base.update(overrides)
    return base


class TcP03608(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P036-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn("acquisition:120", result["preservedResults"])
        self.assertIn("saved:24", result["preservedResults"])

    def test_retained_complete_path_is_not_qualified(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "retained_path")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("acquisition:120", result["preservedResults"])
        self.assertIn("saved:24", result["preservedResults"])
        self.assertTrue(any("not a qualified or allowed" in item for item in result["reasons"]))

    def test_increasing_duration_keeps_separate_rates(self):
        result = evaluate(payload(duration="increasing", savedRate="failing", savedComplete=False,
                                   savedRetained=False))
        self.assertEqual(result["decision"], "withheld")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("acquisition:120", result["preservedResults"])
        self.assertIn("saved:failing", result["preservedResults"])
        self.assertIn("duration:increasing", result["preservedResults"])
        self.assertTrue(any("increasing duration" in item for item in result["reasons"]))

    def test_storage_pressure_does_not_merge_rates(self):
        result = evaluate(payload(storagePressure=True, savedComplete=False, savedRetained=False))
        self.assertEqual(result["decision"], "withheld")
        self.assertIn("storagePressure:true", result["preservedResults"])
        self.assertIn("acquisition:120", result["preservedResults"])
        self.assertIn("saved:24", result["preservedResults"])
        self.assertIn("storage pressure", result["openQuestions"])

    def test_audio_selection_keeps_separate_rates(self):
        result = evaluate(payload(audioSelection="on"))
        self.assertEqual(result["decision"], "retained_path")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("audio:on", result["preservedResults"])
        self.assertIn("acquisition:120", result["preservedResults"])
        self.assertTrue(any("audio selection" in item for item in result["reasons"]))

    def test_elevated_thermal_state_withholds_incomplete_save(self):
        result = evaluate(
            payload(thermalState="elevated", savedRate="failing", savedComplete=False,
                    savedRetained=False)
        )
        self.assertEqual(result["decision"], "withheld")
        self.assertIn("thermal:elevated", result["preservedResults"])
        self.assertIn("acquisition:120", result["preservedResults"])
        self.assertIn("saved:failing", result["preservedResults"])
        self.assertIn("thermal state elevated", result["openQuestions"])

    def test_negative_advertising_discard_speed_fails(self):
        result = evaluate(payload(advertiseAcquisitionAsSaved=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "retained_path"})
        self.assertEqual(result["rejectedClaims"], ["acquisition-advertised-as-saved-raw"])
        self.assertEqual(result["preservedResults"][0], "acquisition:120")
        self.assertEqual(result["preservedResults"][1], "saved:24")
        self.assertNotEqual(result["preservedResults"][1], "saved:120")
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "acquisitionRate": "24", "savedRate": "24"},
            {**valid, "framesDiscarded": False},
            {**valid, "savedRate": "failing", "savedComplete": True},
            {**valid, "duration": "forever"},
            {**valid, "thermalState": "hot"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
