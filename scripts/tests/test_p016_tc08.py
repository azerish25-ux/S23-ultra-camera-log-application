"""TC-P016-08 physical qualification boundary."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p016_tc08", Path(__file__).resolve().parents[1] / "gates" / "p016_tc08.py"
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
_ORACLE = ["file-retained", "playback:separate", "cadence:separate"]


def payload(**overrides):
    base = {
        "durationSec": 60,
        "requiredEnduranceSec": 1800,
        "thermalWarm": False,
        "lensId": "lens-wide",
        "audioSelection": "internal-mic",
        "environmentalEvidence": False,
        "advertisedSize": "1920x1080",
        "higherResolutionClaimed": False,
    }
    base.update(overrides)
    return base


class TcP01608(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P016-08")
        self.assertIn(result["decision"], {"slice_only", "endurance_observed"})
        self.assertNotIn(result["decision"], {"unlimited", "qualified", "allowed"})
        self.assertTrue(result["reasons"])
        for token in _ORACLE:
            self.assertIn(token, result["preservedResults"])

    def test_contract_text_is_encoded(self):
        self.assertIn("short successful physical take", _MODULE.INTERVENTION)
        self.assertIn("higher-resolution", _MODULE.EXPECTED)
        self.assertIn("unlimited recording", _MODULE.NEGATIVE)

    def test_short_cold_run_rejects_unlimited_extrapolation(self):
        source = payload(durationSec=60, requiredEnduranceSec=1800, thermalWarm=False)
        result = evaluate(source)
        self.assertContract(result)
        self.assertEqual(result["decision"], "slice_only")
        self.assertNotIn(result["decision"], {"unlimited", "qualified", "allowed", "endurance_observed"})
        self.assertIn("unlimited-extrapolation", result["rejectedClaims"])
        self.assertEqual(
            result["preservedResults"],
            ["60s", "lens-wide", "internal-mic", "1920x1080", *_ORACLE],
        )
        self.assertIn("endurance unqualified", result["openQuestions"])
        self.assertTrue(any("short cold run" in reason for reason in result["reasons"]))
        self.assertTrue(any("60s is below required endurance 1800s" in reason for reason in result["reasons"]))

    def test_thermal_warmup_short_take_stays_slice_only(self):
        result = evaluate(payload(durationSec=90, thermalWarm=True, lensId="lens-wide"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "slice_only")
        self.assertNotIn("unlimited-extrapolation", result["rejectedClaims"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "unlimited"})
        self.assertIn("lens-wide", result["preservedResults"])
        self.assertIn("90s", result["preservedResults"])
        self.assertIn("endurance unqualified", result["openQuestions"])
        self.assertTrue(any("does not certify endurance" in reason for reason in result["reasons"]))

    def test_different_lens_is_preserved_on_the_slice(self):
        result = evaluate(payload(lensId="lens-tele", audioSelection="internal-mic"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "slice_only")
        self.assertIn("lens-tele", result["preservedResults"])
        self.assertNotIn("lens-wide", result["preservedResults"])
        self.assertIn("1920x1080", result["preservedResults"])
        self.assertIn("unlimited-extrapolation", result["rejectedClaims"])

    def test_changed_audio_selection_is_preserved_on_the_slice(self):
        result = evaluate(payload(audioSelection="usb-mic", lensId="lens-wide"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "slice_only")
        self.assertIn("usb-mic", result["preservedResults"])
        self.assertNotIn("internal-mic", result["preservedResults"])
        self.assertIn("file-retained", result["preservedResults"])

    def test_higher_resolution_claim_stays_unqualified(self):
        result = evaluate(
            payload(
                durationSec=1800,
                requiredEnduranceSec=1800,
                thermalWarm=True,
                environmentalEvidence=True,
                higherResolutionClaimed=True,
                advertisedSize="3840x2160",
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "slice_only")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "endurance_observed"})
        self.assertIn("higher-resolution", result["rejectedClaims"])
        self.assertNotIn("unlimited-extrapolation", result["rejectedClaims"])
        self.assertIn("3840x2160", result["preservedResults"])
        self.assertIn("higher-resolution unqualified", result["openQuestions"])
        self.assertIn("endurance unqualified", result["openQuestions"])

    def test_met_duration_is_not_an_endurance_certificate(self):
        result = evaluate(
            payload(
                durationSec=1800,
                requiredEnduranceSec=1800,
                thermalWarm=True,
                environmentalEvidence=True,
                higherResolutionClaimed=False,
                lensId="lens-wide",
                audioSelection="internal-mic",
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "endurance_observed")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "unlimited", "slice_only"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("not an endurance certificate", result["openQuestions"])
        self.assertIn("not-endurance-certified", result["openQuestions"])
        self.assertTrue(
            any("not a physical S23 endurance certificate" in reason for reason in result["reasons"])
        )
        self.assertIn("1800s", result["preservedResults"])
        self.assertIn("lens-wide", result["preservedResults"])

    def test_missing_environment_keeps_a_long_take_as_a_slice(self):
        result = evaluate(
            payload(
                durationSec=1800,
                requiredEnduranceSec=1800,
                thermalWarm=True,
                environmentalEvidence=False,
            )
        )
        self.assertEqual(result["decision"], "slice_only")
        self.assertNotIn("unlimited-extrapolation", result["rejectedClaims"])
        self.assertTrue(any("environmental evidence is missing" in reason for reason in result["reasons"]))
        self.assertIn("1800s", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "durationSec": -1},
            {**valid, "durationSec": 60.0},
            {**valid, "requiredEnduranceSec": 0},
            {**valid, "thermalWarm": "yes"},
            {**valid, "lensId": ""},
            {**valid, "higherResolutionClaimed": "false"},
            {k: v for k, v in valid.items() if k != "audioSelection"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
