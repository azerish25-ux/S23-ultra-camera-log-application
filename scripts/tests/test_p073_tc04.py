"""TC-P073-04 neutral and saturated stress."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p073_tc04", Path(__file__).resolve().parents[1] / "gates" / "p073_tc04.py"
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
        "sceneId": "scene-alpha",
        "bracket": "under",
        "neutralControlled": True,
        "outputsFinite": True,
        "spectralAccuracy": "unsupported",
        "unboundedCoupling": False,
        "hiddenPerFace": False,
    }
    base.update(overrides)
    return base


class TcP07304(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P073-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_packet_strings(self):
        self.assertIn("neutral steps", _MODULE.INTERVENTION)
        self.assertIn("cross-channel", _MODULE.NEGATIVE)
        self.assertIn("exposure brackets", _MODULE.REPEAT)
        self.assertIn("independently captured scenes", _MODULE.REPEAT)

    def test_under_bracket_records_unsupported_spectral_accuracy(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "neutral_recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("scene-alpha", result["preservedResults"])
        self.assertIn("bracket:under", result["preservedResults"])
        self.assertIn("neutral:true", result["preservedResults"])
        self.assertIn("finite:true", result["preservedResults"])
        self.assertIn("spectral accuracy is unsupported", result["openQuestions"])

    def test_over_bracket_on_another_scene_stays_recorded(self):
        result = evaluate(payload(sceneId="scene-beta", bracket="over"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "neutral_recorded")
        self.assertIn("scene-beta", result["preservedResults"])
        self.assertIn("bracket:over", result["preservedResults"])
        self.assertIn("spectral:unsupported", result["preservedResults"])

    def test_unbounded_coupling_fails_and_keeps_the_scene(self):
        result = evaluate(payload(unboundedCoupling=True, bracket="nominal"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["unbounded-coupling"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("scene-alpha", result["preservedResults"])
        self.assertIn("bracket:nominal", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "neutral_recorded"})

    def test_hidden_per_face_correction_fails(self):
        result = evaluate(payload(hiddenPerFace=True, sceneId="scene-gamma"))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["hidden-per-face"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("scene-gamma", result["preservedResults"])

    def test_non_finite_output_is_rejected_without_wiping_neutrals(self):
        result = evaluate(payload(outputsFinite=False, neutralControlled=False))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["non-finite-output", "neutral-uncontrolled"])
        self.assertIn("finite:false", result["preservedResults"])
        self.assertIn("neutral:false", result["preservedResults"])
        self.assertIn("scene-alpha", result["preservedResults"])

    def test_supported_spectral_flag_is_withheld(self):
        result = evaluate(payload(spectralAccuracy="supported"))
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("spectral:supported", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "neutral_recorded"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "sceneId"},
            {**valid, "extra": True},
            {**valid, "sceneId": "Scene Alpha"},
            {**valid, "bracket": "middle"},
            {**valid, "spectralAccuracy": "measured"},
            {**valid, "neutralControlled": 1},
            {**valid, "hiddenPerFace": "false"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
