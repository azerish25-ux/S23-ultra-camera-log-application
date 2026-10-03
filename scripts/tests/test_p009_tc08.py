"""TC-P009-08 physical qualification boundary."""

from __future__ import annotations

import importlib.util
import math
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p009_tc08", Path(__file__).resolve().parents[1] / "gates" / "p009_tc08.py"
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


def take(**overrides):
    base = {
        "durationSec": 12,
        "requiredEnduranceSec": 600,
        "thermalWarm": False,
        "lensId": "rear-tele",
        "audioSelection": "internal",
        "environmentalEvidence": False,
    }
    base.update(overrides)
    return base


class TcP00908(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P009-08")
        self.assertIn(result["decision"], {"slice_only", "endurance_observed"})
        self.assertNotIn(result["decision"], {"unlimited", "qualified"})
        self.assertIsInstance(result["reasons"], list)
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for reason in result["reasons"]:
            self.assertNotIn("unlimited", reason)
            self.assertNotIn("qualified", reason)
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) for item in result[key]))

    def assertSlice(self, result, duration, lens_id, audio, extrapolated):
        self.assertContract(result)
        self.assertEqual(result["decision"], "slice_only")
        self.assertNotIn(result["decision"], {"unlimited", "qualified"})
        self.assertEqual(
            result["preservedResults"],
            [f"duration:{duration}", lens_id, audio],
        )
        self.assertIn(f"duration:{duration}", result["preservedResults"])
        self.assertIn(lens_id, result["preservedResults"])
        self.assertIn(audio, result["preservedResults"])
        self.assertIn("endurance unqualified", result["openQuestions"])
        if extrapolated:
            self.assertIn("unlimited-extrapolation", result["rejectedClaims"])
            self.assertEqual(result["rejectedClaims"], ["unlimited-extrapolation"])
        else:
            self.assertNotIn("unlimited-extrapolation", result["rejectedClaims"])
            self.assertEqual(result["rejectedClaims"], [])

    def test_short_cold_run_is_slice_only_not_unlimited(self):
        result = evaluate(
            take(
                durationSec=8,
                requiredEnduranceSec=1800,
                thermalWarm=False,
                lensId="rear-tele",
                audioSelection="cam-mic",
                environmentalEvidence=False,
            )
        )
        self.assertSlice(result, 8, "rear-tele", "cam-mic", extrapolated=True)
        self.assertTrue(any("rear-tele" in item and "cam-mic" in item for item in result["reasons"]))

    def test_short_cold_run_with_environmental_evidence_still_cannot_extrapolate(self):
        result = evaluate(
            take(
                durationSec=30,
                requiredEnduranceSec=600,
                thermalWarm=False,
                environmentalEvidence=True,
                lensId="rear-wide",
                audioSelection="lav",
            )
        )
        self.assertSlice(result, 30, "rear-wide", "lav", extrapolated=True)
        self.assertNotEqual(result["decision"], "endurance_observed")
        self.assertNotEqual(result["decision"], "unlimited")

    def test_thermal_warmup_still_short_of_required_duration(self):
        result = evaluate(
            take(
                durationSec=120,
                requiredEnduranceSec=1800,
                thermalWarm=True,
                lensId="rear-wide",
                audioSelection="lav",
                environmentalEvidence=True,
            )
        )
        self.assertSlice(result, 120, "rear-wide", "lav", extrapolated=False)
        self.assertNotEqual(result["decision"], "endurance_observed")
        self.assertNotIn("unlimited", result["decision"])

    def test_warm_short_without_environmental_evidence_stays_a_slice(self):
        result = evaluate(
            take(
                durationSec=45,
                requiredEnduranceSec=90,
                thermalWarm=True,
                environmentalEvidence=False,
                lensId="front",
                audioSelection="none",
            )
        )
        self.assertSlice(result, 45, "front", "none", extrapolated=False)

    def test_different_lens_is_preserved_and_not_swapped(self):
        cold = evaluate(
            take(durationSec=5, requiredEnduranceSec=60, thermalWarm=False, lensId="wide-1x", audioSelection="internal")
        )
        other = evaluate(
            take(durationSec=5, requiredEnduranceSec=60, thermalWarm=False, lensId="tele-3x", audioSelection="internal")
        )
        self.assertSlice(cold, 5, "wide-1x", "internal", extrapolated=True)
        self.assertSlice(other, 5, "tele-3x", "internal", extrapolated=True)
        self.assertNotIn("tele-3x", cold["preservedResults"])
        self.assertNotIn("wide-1x", other["preservedResults"])
        self.assertNotIn("tele-3x", " ".join(cold["reasons"]))
        self.assertIn("wide-1x", " ".join(cold["reasons"]))
        self.assertIn("tele-3x", " ".join(other["reasons"]))

    def test_changed_audio_selection_is_preserved(self):
        first = evaluate(
            take(
                durationSec=15,
                requiredEnduranceSec=120,
                thermalWarm=True,
                lensId="rear-tele",
                audioSelection="cam-mic",
                environmentalEvidence=False,
            )
        )
        changed = evaluate(
            take(
                durationSec=15,
                requiredEnduranceSec=120,
                thermalWarm=True,
                lensId="rear-tele",
                audioSelection="external-lav",
                environmentalEvidence=False,
            )
        )
        self.assertSlice(first, 15, "rear-tele", "cam-mic", extrapolated=False)
        self.assertSlice(changed, 15, "rear-tele", "external-lav", extrapolated=False)
        self.assertNotIn("external-lav", first["preservedResults"])
        self.assertNotIn("cam-mic", changed["preservedResults"])
        self.assertIn("cam-mic", " ".join(first["reasons"]))
        self.assertIn("external-lav", " ".join(changed["reasons"]))

    def test_duration_meeting_requirement_with_evidence_is_endurance_not_unlimited(self):
        for lens_id, audio in (
            ("rear-tele", "cam-mic"),
            ("front-ultrawide", "external-lav"),
        ):
            result = evaluate(
                take(
                    durationSec=1800,
                    requiredEnduranceSec=1800,
                    thermalWarm=True,
                    lensId=lens_id,
                    audioSelection=audio,
                    environmentalEvidence=True,
                )
            )
            self.assertContract(result)
            self.assertEqual(result["decision"], "endurance_observed")
            self.assertNotIn(result["decision"], {"unlimited", "qualified", "slice_only"})
            self.assertEqual(result["rejectedClaims"], [])
            self.assertEqual(result["openQuestions"], [])
            self.assertEqual(
                result["preservedResults"],
                ["duration:1800", lens_id, audio],
            )
            text = " ".join(result["reasons"])
            self.assertIn(lens_id, text)
            self.assertIn(audio, text)
            self.assertIn("lens", text)
            self.assertIn("audio", text)
            self.assertNotIn("unlimited", text)

    def test_cold_run_that_meets_duration_and_evidence_is_observed_not_extrapolated(self):
        result = evaluate(
            take(
                durationSec=600,
                requiredEnduranceSec=600,
                thermalWarm=False,
                environmentalEvidence=True,
                lensId="rear-wide",
                audioSelection="boom",
            )
        )
        self.assertEqual(result["decision"], "endurance_observed")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertNotIn("unlimited-extrapolation", result["rejectedClaims"])
        self.assertEqual(result["openQuestions"], [])
        self.assertIn("rear-wide", result["preservedResults"])
        self.assertIn("boom", result["preservedResults"])
        text = " ".join(result["reasons"])
        self.assertIn("lens", text)
        self.assertIn("audio", text)
        self.assertIn("rear-wide", text)
        self.assertIn("boom", text)

    def test_met_duration_without_environmental_evidence_stays_slice_only(self):
        result = evaluate(
            take(
                durationSec=900,
                requiredEnduranceSec=600,
                thermalWarm=False,
                environmentalEvidence=False,
                lensId="tele-3x",
                audioSelection="external-lav",
            )
        )
        self.assertSlice(result, 900, "tele-3x", "external-lav", extrapolated=False)
        self.assertNotEqual(result["decision"], "endurance_observed")

    def test_float_duration_uses_default_string_form(self):
        result = evaluate(
            take(
                durationSec=12.5,
                requiredEnduranceSec=40,
                thermalWarm=False,
                lensId="rear-tele",
                audioSelection="internal",
            )
        )
        self.assertSlice(result, 12.5, "rear-tele", "internal", extrapolated=True)
        self.assertIn("duration:12.5", result["preservedResults"])

    def test_just_below_required_cold_is_extrapolation(self):
        result = evaluate(
            take(durationSec=59.9, requiredEnduranceSec=60, thermalWarm=False, environmentalEvidence=True)
        )
        self.assertEqual(result["decision"], "slice_only")
        self.assertIn("unlimited-extrapolation", result["rejectedClaims"])
        self.assertIn("duration:59.9", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = take()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "lensId"},
            {**valid, "extra": True},
            {**valid, "durationSec": True},
            {**valid, "durationSec": -1},
            {**valid, "durationSec": "12"},
            {**valid, "durationSec": math.nan},
            {**valid, "durationSec": math.inf},
            {**valid, "requiredEnduranceSec": 0},
            {**valid, "requiredEnduranceSec": -5},
            {**valid, "requiredEnduranceSec": True},
            {**valid, "requiredEnduranceSec": math.nan},
            {**valid, "thermalWarm": "false"},
            {**valid, "thermalWarm": 0},
            {**valid, "lensId": ""},
            {**valid, "lensId": None},
            {**valid, "audioSelection": ""},
            {**valid, "audioSelection": 1},
            {**valid, "environmentalEvidence": 1},
            {**valid, "environmentalEvidence": "false"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
