"""TC-P040-08 throughput stage conflation."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p040_tc08", Path(__file__).resolve().parents[1] / "gates" / "p040_tc08.py"
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


class TcP04008(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P040-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_intervention_expected_and_negative_are_encoded(self):
        self.assertIn("acquisition-only", _MODULE.INTERVENTION)
        self.assertIn("separate stage rates", _MODULE.EXPECTED)
        self.assertIn("discarded-frame acquisition speed", _MODULE.NEGATIVE)

    def test_retained_complete_path_keeps_rates_separate(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "retained_path")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("acquisition:120", result["preservedResults"])
        self.assertIn("saved:24", result["preservedResults"])
        self.assertIn("duration:baseline", result["preservedResults"])
        self.assertTrue(any("not a qualified or allowed" in item for item in result["reasons"]))
        self.assertIn(
            "acquisition-only rate is not saved RAW recording performance",
            result["openQuestions"],
        )

    def test_negative_advertises_acquisition_as_saved_raw(self):
        result = evaluate(payload(advertiseAcquisitionAsSaved=True, duration="increasing"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "retained_path"})
        self.assertEqual(result["rejectedClaims"], ["acquisition-advertised-as-saved-raw"])
        self.assertIn("acquisition:120", result["preservedResults"])
        self.assertIn("saved:24", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertTrue(any("increasing duration" in item for item in result["reasons"]))

    def test_increasing_duration_does_not_merge_stage_rates(self):
        result = evaluate(payload(duration="increasing"))
        self.assertEqual(result["decision"], "retained_path")
        self.assertIn("duration:increasing", result["preservedResults"])
        self.assertIn("acquisition:120", result["preservedResults"])
        self.assertIn("saved:24", result["preservedResults"])
        self.assertTrue(any("increasing duration did not merge" in item for item in result["reasons"]))

    def test_storage_pressure_failing_saved_path_is_withheld(self):
        result = evaluate(
            payload(
                savedRate="failing",
                savedComplete=False,
                savedRetained=False,
                storagePressure=True,
                duration="increasing",
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "retained_path"})
        self.assertIn("saved:failing", result["preservedResults"])
        self.assertIn("acquisition:120", result["preservedResults"])
        self.assertIn("storagePressure:true", result["preservedResults"])
        self.assertIn("storage pressure", result["openQuestions"])
        self.assertIn("saved-source experiment failing", result["openQuestions"])

    def test_audio_selection_does_not_merge_stage_rates(self):
        result = evaluate(payload(audioSelection="on"))
        self.assertEqual(result["decision"], "retained_path")
        self.assertIn("audio:on", result["preservedResults"])
        self.assertIn("acquisition:120", result["preservedResults"])
        self.assertTrue(any("audio selection did not merge" in item for item in result["reasons"]))

    def test_elevated_thermal_failing_saved_path_is_withheld(self):
        result = evaluate(
            payload(
                savedRate="failing",
                savedComplete=False,
                savedRetained=False,
                thermalState="elevated",
            )
        )
        self.assertEqual(result["decision"], "withheld")
        self.assertIn("thermal:elevated", result["preservedResults"])
        self.assertIn("acquisition:120", result["preservedResults"])
        self.assertIn("thermal state elevated", result["openQuestions"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "savedRate"},
            {**valid, "extra": True},
            {**valid, "acquisitionRate": "24", "savedRate": "24"},
            {**valid, "acquisitionRate": "10", "savedRate": "30"},
            {**valid, "framesDiscarded": False},
            {**valid, "savedRate": "failing", "savedComplete": True},
            {**valid, "duration": "endless"},
            {**valid, "thermalState": "severe"},
            {**valid, "audioSelection": "maybe"},
            {**valid, "storagePressure": "yes"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
