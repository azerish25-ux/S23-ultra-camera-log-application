"""TC-P010-08 physical qualification boundary."""

from __future__ import annotations

import importlib.util
import math
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p010_tc08", Path(__file__).resolve().parents[1] / "gates" / "p010_tc08.py"
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
        "durationSec": 5,
        "requiredEnduranceSec": 30,
        "thermalWarm": False,
        "lensId": "lens-wide",
        "audioSelection": "internal-mic",
        "environmentalEvidence": False,
        "advertisedSize": "1920x1080",
    }
    base.update(overrides)
    return base


class TcP01008(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P010-08")
        self.assertIn(result["decision"], {"slice_only", "endurance_observed"})
        self.assertNotIn(result["decision"], {"unlimited", "qualified", "allowed"})
        self.assertIsInstance(result["reasons"], list)
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        self.assertIsInstance(result["rejectedClaims"], list)
        self.assertTrue(all(isinstance(item, str) and item for item in result["rejectedClaims"]))
        self.assertIsInstance(result["preservedResults"], list)
        self.assertIsInstance(result["openQuestions"], list)
        self.assertTrue(all(isinstance(item, str) for item in result["openQuestions"]))

    def assertSlice(self, result, source):
        self.assertContract(result)
        self.assertEqual(result["decision"], "slice_only")
        self.assertNotIn(result["decision"], {"unlimited", "qualified"})
        self.assertEqual(
            result["preservedResults"],
            [
                source["durationSec"],
                source["lensId"],
                source["audioSelection"],
                source["advertisedSize"],
            ],
        )
        self.assertEqual(result["openQuestions"], ["endurance unqualified"])
        self.assertIn(source["advertisedSize"], result["preservedResults"])
        self.assertIn(source["lensId"], result["preservedResults"])
        self.assertIn(source["audioSelection"], result["preservedResults"])
        self.assertIn(source["durationSec"], result["preservedResults"])

    def test_cold_short_run_rejects_unlimited_extrapolation(self):
        source = payload(
            durationSec=5,
            requiredEnduranceSec=30,
            thermalWarm=False,
            environmentalEvidence=False,
            lensId="lens-wide",
            audioSelection="internal-mic",
            advertisedSize="1920x1080",
        )
        result = evaluate(source)
        self.assertSlice(result, source)
        self.assertEqual(result["rejectedClaims"], ["unlimited-extrapolation"])
        self.assertTrue(any("short cold run" in item for item in result["reasons"]))
        self.assertTrue(any("does not certify endurance" in item for item in result["reasons"]))

    def test_warm_but_still_short_stays_slice_only(self):
        source = payload(
            durationSec=8,
            requiredEnduranceSec=120,
            thermalWarm=True,
            environmentalEvidence=True,
            lensId="lens-wide",
            audioSelection="internal-mic",
            advertisedSize="3840x2160",
        )
        result = evaluate(source)
        self.assertSlice(result, source)
        self.assertEqual(result["rejectedClaims"], [])
        self.assertNotIn("unlimited-extrapolation", result["rejectedClaims"])
        self.assertNotIn(result["decision"], {"unlimited", "qualified", "endurance_observed"})

    def test_different_lens_is_preserved_on_a_short_take(self):
        source = payload(
            durationSec=4,
            requiredEnduranceSec=30,
            thermalWarm=True,
            environmentalEvidence=False,
            lensId="lens-tele",
            audioSelection="internal-mic",
            advertisedSize="4080x3072",
        )
        result = evaluate(source)
        self.assertSlice(result, source)
        self.assertIn("lens-tele", result["preservedResults"])
        self.assertNotIn("lens-wide", result["preservedResults"])
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["decision"], "slice_only")

    def test_changed_audio_is_preserved_on_a_cold_short_run(self):
        source = payload(
            durationSec=6,
            requiredEnduranceSec=45,
            thermalWarm=False,
            environmentalEvidence=False,
            lensId="lens-wide",
            audioSelection="lav-mic",
            advertisedSize="1920x1080",
        )
        result = evaluate(source)
        self.assertSlice(result, source)
        self.assertIn("lav-mic", result["preservedResults"])
        self.assertNotIn("internal-mic", result["preservedResults"])
        self.assertEqual(result["rejectedClaims"], ["unlimited-extrapolation"])
        self.assertNotIn(result["decision"], {"unlimited", "qualified"})

    def test_cold_short_with_evidence_still_rejects_extrapolation(self):
        source = payload(
            durationSec=9,
            requiredEnduranceSec=10,
            thermalWarm=False,
            environmentalEvidence=True,
            lensId="lens-uw",
            audioSelection="boom",
            advertisedSize="1280x720",
        )
        result = evaluate(source)
        self.assertSlice(result, source)
        self.assertEqual(result["rejectedClaims"], ["unlimited-extrapolation"])
        self.assertEqual(result["openQuestions"], ["endurance unqualified"])

    def test_duration_met_without_evidence_is_slice_only_not_unlimited(self):
        source = payload(
            durationSec=30,
            requiredEnduranceSec=30,
            thermalWarm=False,
            environmentalEvidence=False,
            lensId="lens-wide",
            audioSelection="internal-mic",
            advertisedSize="1920x1080",
        )
        result = evaluate(source)
        self.assertSlice(result, source)
        self.assertEqual(result["rejectedClaims"], [])
        self.assertNotIn("unlimited-extrapolation", result["rejectedClaims"])
        self.assertNotEqual(result["decision"], "endurance_observed")

    def test_duration_met_with_evidence_is_endurance_observed_not_unlimited(self):
        source = payload(
            durationSec=30,
            requiredEnduranceSec=30,
            thermalWarm=False,
            environmentalEvidence=True,
            lensId="lens-wide",
            audioSelection="internal-mic",
            advertisedSize="4000x3000",
        )
        result = evaluate(source)
        self.assertContract(result)
        self.assertEqual(result["decision"], "endurance_observed")
        self.assertNotIn(result["decision"], {"unlimited", "qualified", "slice_only"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["openQuestions"], [])
        self.assertNotIn("endurance unqualified", result["openQuestions"])
        self.assertEqual(
            result["preservedResults"],
            [30, "lens-wide", "internal-mic", "4000x3000"],
        )
        self.assertTrue(any("not an unlimited" in item for item in result["reasons"]))

    def test_longer_warm_run_with_evidence_is_observed_and_keeps_identity(self):
        source = payload(
            durationSec=95,
            requiredEnduranceSec=60,
            thermalWarm=True,
            environmentalEvidence=True,
            lensId="lens-tele",
            audioSelection="headset",
            advertisedSize="4080x3072",
        )
        result = evaluate(source)
        self.assertContract(result)
        self.assertEqual(result["decision"], "endurance_observed")
        self.assertNotEqual(result["decision"], "unlimited")
        self.assertEqual(
            result["preservedResults"],
            [95, "lens-tele", "headset", "4080x3072"],
        )
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["openQuestions"], [])

    def test_fractional_short_duration_is_preserved_exactly(self):
        source = payload(
            durationSec=29.5,
            requiredEnduranceSec=30,
            thermalWarm=True,
            environmentalEvidence=True,
            advertisedSize="1920x1080",
        )
        result = evaluate(source)
        self.assertSlice(result, source)
        self.assertEqual(result["preservedResults"][0], 29.5)
        self.assertNotIn("unlimited-extrapolation", result["rejectedClaims"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "durationSec"},
            {k: v for k, v in valid.items() if k != "advertisedSize"},
            {**valid, "extra": True},
            {**valid, "durationSec": True},
            {**valid, "durationSec": -1},
            {**valid, "durationSec": math.nan},
            {**valid, "durationSec": math.inf},
            {**valid, "durationSec": "5"},
            {**valid, "requiredEnduranceSec": 0},
            {**valid, "requiredEnduranceSec": -5},
            {**valid, "requiredEnduranceSec": True},
            {**valid, "requiredEnduranceSec": math.nan},
            {**valid, "requiredEnduranceSec": "30"},
            {**valid, "thermalWarm": 1},
            {**valid, "thermalWarm": "false"},
            {**valid, "thermalWarm": None},
            {**valid, "lensId": ""},
            {**valid, "lensId": None},
            {**valid, "lensId": 24},
            {**valid, "audioSelection": ""},
            {**valid, "audioSelection": None},
            {**valid, "environmentalEvidence": "yes"},
            {**valid, "environmentalEvidence": 0},
            {**valid, "advertisedSize": ""},
            {**valid, "advertisedSize": None},
            {**valid, "advertisedSize": 1920},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
