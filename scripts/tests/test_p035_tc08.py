"""TC-P035-08 throughput stage conflation."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p035_tc08", Path(__file__).resolve().parents[1] / "gates" / "p035_tc08.py"
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
        "savedStatus": "complete",
        "discardedFrames": False,
        "advertiseAcquisitionAsSaved": False,
        "duration": "short",
        "storagePressure": False,
        "audioSelected": False,
        "thermal": "nominal",
    }
    base.update(overrides)
    return base


class TcP03508(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P035-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_clean_retained_path_keeps_rates_separate(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "retained_path")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("acquisition:120", result["preservedResults"])
        self.assertIn("saved:24", result["preservedResults"])
        self.assertTrue(any("not physical S23 qualification" in item for item in result["reasons"]))
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_repeat_increasing_duration_does_not_merge_rates(self):
        result = evaluate(payload(duration="increasing"))
        self.assertEqual(result["decision"], "retained_path")
        self.assertIn("acquisition:120", result["preservedResults"])
        self.assertIn("saved:24", result["preservedResults"])
        self.assertIn("duration:increasing", result["preservedResults"])
        self.assertIn("increasing duration is not a measured cadence", result["openQuestions"])

    def test_repeat_storage_pressure_and_audio(self):
        storage = evaluate(payload(storagePressure=True, savedStatus="slower", savedFps="12"))
        audio = evaluate(payload(audioSelected=True))
        self.assertEqual(storage["decision"], "stage_separated")
        self.assertIn("acquisition:120", storage["preservedResults"])
        self.assertIn("saved:12", storage["preservedResults"])
        self.assertIn("storage pressure", storage["openQuestions"])
        self.assertEqual(audio["decision"], "stage_separated")
        self.assertIn("audio selected", audio["openQuestions"])
        self.assertIn("saved:24", audio["preservedResults"])

    def test_repeat_thermal_state(self):
        result = evaluate(payload(thermal="severe", savedStatus="failed", savedFps="0"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "stage_separated")
        self.assertIn("thermal:severe", result["preservedResults"])
        self.assertIn("acquisition:120", result["preservedResults"])
        self.assertIn("saved:0", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "retained_path"})

    def test_negative_acquisition_advertised_as_saved(self):
        result = evaluate(
            payload(advertiseAcquisitionAsSaved=True, discardedFrames=True, savedStatus="failed", savedFps="0")
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["acquisition-advertised-as-saved"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("acquisition:120", result["preservedResults"])
        self.assertIn("saved:0", result["preservedResults"])
        self.assertFalse(any(item == "saved:120" for item in result["preservedResults"]))

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "acquisitionFps": "0"},
            {**valid, "savedFps": "fast"},
            {**valid, "savedStatus": "complete", "savedFps": "0"},
            {**valid, "thermal": "hot"},
            {**valid, "discardedFrames": "yes"},
            {key: value for key, value in valid.items() if key != "duration"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
