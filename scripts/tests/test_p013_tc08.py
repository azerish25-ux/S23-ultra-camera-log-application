"""TC-P013-08 a short cold run is not unlimited recording."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p013_tc08", Path(__file__).resolve().parents[1] / "gates" / "p013_tc08.py"
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
_SIZE = "1920x1080"


def payload(**overrides):
    base = {
        "durationSec": 10,
        "requiredEnduranceSec": 60,
        "thermalWarm": False,
        "lensId": "rear-main",
        "audioSelection": "camcorder",
        "environmentalEvidence": False,
        "advertisedSize": _SIZE,
    }
    base.update(overrides)
    return base


class TcP01308(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P013-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "unlimited"})
        self.assertIn(result["decision"], {"slice_only", "endurance_observed"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) and item for item in result[key]))
        self.assertIn("higher-resolution claims unqualified", result["openQuestions"])

    def test_short_cold_run_does_not_extrapolate(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "slice_only")
        self.assertIn("unlimited-extrapolation", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"], ["10", "rear-main", "camcorder", _SIZE])
        self.assertIn("endurance unqualified", result["openQuestions"])
        self.assertTrue(any("short cold run" in item for item in result["reasons"]))
        self.assertNotIn(result["decision"], {"qualified", "allowed", "unlimited"})

    def test_thermal_warmup_short_take_is_still_a_slice(self):
        result = evaluate(payload(thermalWarm=True, durationSec=20, lensId="rear-tele"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "slice_only")
        self.assertNotIn("unlimited-extrapolation", result["rejectedClaims"])
        self.assertIn("20", result["preservedResults"])
        self.assertIn("rear-tele", result["preservedResults"])
        self.assertIn(_SIZE, result["preservedResults"])
        self.assertIn("endurance unqualified", result["openQuestions"])

    def test_different_lens_is_preserved_on_the_slice(self):
        result = evaluate(payload(lensId="ultrawide", audioSelection="mic"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "slice_only")
        self.assertEqual(result["preservedResults"], ["10", "ultrawide", "mic", _SIZE])

    def test_changed_audio_selection_does_not_upgrade_the_slice(self):
        result = evaluate(payload(audioSelection="unprocessed", environmentalEvidence=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "slice_only")
        self.assertIn("unprocessed", result["preservedResults"])
        self.assertIn("unlimited-extrapolation", result["rejectedClaims"])
        self.assertNotIn(result["decision"], {"endurance_observed", "qualified", "allowed"})

    def test_met_endurance_is_observed_not_unlimited_or_qualified(self):
        result = evaluate(
            payload(
                durationSec=60,
                requiredEnduranceSec=60,
                thermalWarm=True,
                environmentalEvidence=True,
                lensId="rear-main",
                audioSelection="camcorder",
                advertisedSize="3840x2160",
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "endurance_observed")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "unlimited"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"], ["60", "rear-main", "camcorder", "3840x2160"])
        self.assertNotIn("endurance unqualified", result["openQuestions"])
        self.assertIn("higher-resolution claims unqualified", result["openQuestions"])
        self.assertTrue(any("not an unlimited recording claim" in item for item in result["reasons"]))

    def test_missing_environment_on_a_long_take_stays_a_slice(self):
        result = evaluate(
            payload(durationSec=90, environmentalEvidence=False, thermalWarm=True)
        )
        self.assertEqual(result["decision"], "slice_only")
        self.assertIn("90", result["preservedResults"])
        self.assertIn("endurance unqualified", result["openQuestions"])
        self.assertTrue(any("environmental evidence is missing" in item for item in result["reasons"]))

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "durationSec": -1},
            {**valid, "requiredEnduranceSec": 0},
            {**valid, "thermalWarm": "yes"},
            {**valid, "lensId": ""},
            {**valid, "environmentalEvidence": 1},
            {k: v for k, v in valid.items() if k != "advertisedSize"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
