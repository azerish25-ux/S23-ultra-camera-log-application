"""TC-P044-01 neutral target invalidity."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p044_tc01", Path(__file__).resolve().parents[1] / "gates" / "p044_tc01.py"
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
        "patchId": "neutral-1",
        "defect": "none",
        "wholeFrameMean": "7200",
        "knownNeutral": True,
        "substituteMean": False,
    }
    base.update(overrides)
    return base


class TcP04401(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P044-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))

    def test_constants_encode_intervention_expected_and_negative(self):
        self.assertIn("clipped, textured, specular", _MODULE.INTERVENTION)
        self.assertIn("provisional", _MODULE.EXPECTED)
        self.assertIn("Whole-image average brightness", _MODULE.NEGATIVE)

    def test_known_neutral_is_provisional_not_measured(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "provisional")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("patch:neutral-1", result["preservedResults"])
        self.assertIn("whole-frame-mean:7200", result["preservedResults"])
        self.assertIn("explicitly provisional; not a measured profile", result["reasons"])

    def test_dark_patch_repeat_rejects_without_dropping_the_mean(self):
        result = evaluate(payload(defect="dark", patchId="dark-patch"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["invalid-neutral:dark"])
        self.assertIn("patch:dark-patch", result["preservedResults"])
        self.assertIn("whole-frame-mean:7200", result["preservedResults"])
        self.assertIn("defect:dark", result["preservedResults"])

    def test_partial_clip_repeat_rejects_the_region(self):
        result = evaluate(payload(defect="partial_clip", wholeFrameMean="1800"))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "provisional"})
        self.assertEqual(result["rejectedClaims"], ["invalid-neutral:partial_clip"])
        self.assertIn("whole-frame-mean:1800", result["preservedResults"])
        self.assertIn("defect:partial_clip", result["preservedResults"])

    def test_colored_illumination_repeat_is_not_a_neutral_target(self):
        result = evaluate(payload(defect="colored", patchId="amber"))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["invalid-neutral:colored"])
        self.assertIn("patch:amber", result["preservedResults"])

    def test_negative_mean_substitution_cannot_qualify(self):
        result = evaluate(payload(substituteMean=True, knownNeutral=True, defect="none"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "provisional"})
        self.assertEqual(result["rejectedClaims"], ["whole-frame-mean-substitution"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("patch:neutral-1", result["preservedResults"])
        self.assertIn("whole-frame-mean:7200", result["preservedResults"])
        self.assertIn("known-neutral:true", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "defect"},
            {**valid, "extra": True},
            {**valid, "defect": "hot"},
            {**valid, "wholeFrameMean": "07200"},
            {**valid, "wholeFrameMean": 7200},
            {**valid, "knownNeutral": "true"},
            {**valid, "substituteMean": 1},
            {**valid, "patchId": ""},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
