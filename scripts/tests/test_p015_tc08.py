"""TC-P015-08 a short cold run is not unlimited recording."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p015_tc08", Path(__file__).resolve().parents[1] / "gates" / "p015_tc08.py"
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
        "durationSec": 15,
        "requiredEnduranceSec": 60,
        "thermalWarm": False,
        "lensId": "lens-wide",
        "audioSelection": "internal-mic",
        "environmentalEvidence": False,
        "extrapolateUnlimited": True,
    }
    base.update(overrides)
    return base


class TcP01508(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P015-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "unlimited"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))

    def test_contract_text(self):
        self.assertIn("short successful physical take", _MODULE.INTERVENTION)
        self.assertIn("higher-resolution", _MODULE.EXPECTED)
        self.assertIn("unlimited recording", _MODULE.NEGATIVE)
        self.assertIn("thermal warm-up", _MODULE.REPEAT)

    def test_short_cold_extrapolation_fails(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "slice_only")
        self.assertEqual(result["rejectedClaims"], ["unlimited-recording"])
        self.assertEqual(result["preservedResults"], ["15s", "lens-wide", "internal-mic"])
        self.assertEqual(
            result["openQuestions"],
            ["endurance unqualified", "higher-resolution unqualified"],
        )
        self.assertTrue(any("15s" in item or "15" in item for item in result["reasons"]))
        self.assertTrue(any("unlimited recording" in item for item in result["reasons"]))

    def test_thermal_warm_up_still_does_not_certify_endurance(self):
        result = evaluate(payload(thermalWarm=True, extrapolateUnlimited=False))
        self.assertEqual(result["decision"], "slice_only")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "observed"})
        self.assertIn("15s", result["preservedResults"])
        self.assertIn("endurance unqualified", result["openQuestions"])
        self.assertIn("higher-resolution unqualified", result["openQuestions"])
        self.assertNotIn("unlimited-recording", result["rejectedClaims"])
        self.assertTrue(any("thermal warm-up" in item for item in result["reasons"]))

    def test_different_lens_is_preserved_on_the_slice(self):
        result = evaluate(payload(lensId="lens-tele", extrapolateUnlimited=True))
        self.assertEqual(result["decision"], "slice_only")
        self.assertIn("lens-tele", result["preservedResults"])
        self.assertNotIn("lens-wide", result["preservedResults"])
        self.assertIn("unlimited-recording", result["rejectedClaims"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_changed_audio_selection_is_preserved(self):
        result = evaluate(payload(audioSelection="lav-mic", environmentalEvidence=True))
        self.assertEqual(result["decision"], "slice_only")
        self.assertIn("lav-mic", result["preservedResults"])
        self.assertNotIn("internal-mic", result["preservedResults"])
        self.assertIn("15s", result["preservedResults"])
        self.assertIn("endurance unqualified", result["openQuestions"])

    def test_met_duration_still_leaves_higher_resolution_unqualified(self):
        result = evaluate(
            payload(
                durationSec=60,
                thermalWarm=True,
                environmentalEvidence=True,
                extrapolateUnlimited=False,
            )
        )
        self.assertEqual(result["decision"], "observed")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "unlimited"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"], ["60s", "lens-wide", "internal-mic"])
        self.assertEqual(result["openQuestions"], ["higher-resolution unqualified"])
        self.assertNotIn("endurance unqualified", result["openQuestions"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "durationSec": -1},
            {**valid, "requiredEnduranceSec": 0},
            {**valid, "thermalWarm": "yes"},
            {**valid, "lensId": ""},
            {**valid, "extrapolateUnlimited": 1},
            {k: v for k, v in valid.items() if k != "audioSelection"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
