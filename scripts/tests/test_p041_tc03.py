"""TC-P041-03 matrix convention mismatch."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p041_tc03", Path(__file__).resolve().parents[1] / "gates" / "p041_tc03.py"
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
        "fault": "none",
        "determinantFinite": True,
        "neutralVector": "0.33,0.33,0.34",
        "colorVector": "0.2,0.7,0.1",
    }
    base.update(overrides)
    return base


class TcP04103(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P041-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "certified"})
        self.assertTrue(result["reasons"])

    def test_finite_determinant_does_not_certify_a_transposed_matrix(self):
        result = evaluate(payload(fault="transposed"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(
            result["rejectedClaims"],
            ["transposed", "neutral-check-failed", "color-vector-check-failed"],
        )
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("neutral:0.33,0.33,0.34", result["preservedResults"])
        self.assertIn("color:0.2,0.7,0.1", result["preservedResults"])
        self.assertIn("determinantFinite:true", result["preservedResults"])

    def test_reversed_transform_fails_both_checks(self):
        result = evaluate(payload(fault="reversed"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("reversed", result["rejectedClaims"])
        self.assertIn("neutral-check-failed", result["rejectedClaims"])
        self.assertIn("color-vector-check-failed", result["rejectedClaims"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "certified"})

    def test_wrong_white_point_repeat_names_the_convention_error(self):
        result = evaluate(payload(fault="wrong-white-point", neutralVector="D65-neutral"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"][0], "wrong-white-point")
        self.assertIn("neutral:D65-neutral", result["preservedResults"])
        self.assertIn("independent neutral check failed", result["reasons"])

    def test_duplicated_white_balance_repeat_is_not_certified(self):
        result = evaluate(payload(fault="duplicated-white-balance", colorVector="wb,wb,1"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("duplicated-white-balance", result["rejectedClaims"])
        self.assertIn("color:wb,wb,1", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_swapped_direction_repeat_keeps_the_vectors(self):
        result = evaluate(payload(fault="swapped-direction"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("swapped-direction", result["rejectedClaims"])
        self.assertIn("fault:swapped-direction", result["preservedResults"])
        self.assertIn("color-vector-check-failed", result["rejectedClaims"])
        self.assertEqual(_MODULE.EXPECTED[:4], "Fail")

    def test_non_finite_determinant_is_rejected_without_certification(self):
        result = evaluate(payload(determinantFinite=False))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["non-finite-determinant"])
        self.assertIn("determinantFinite:false", result["preservedResults"])
        self.assertNotIn(_MODULE.NEGATIVE, result["reasons"])

    def test_matching_convention_is_checked_not_certified(self):
        result = evaluate(payload())
        self.assertEqual(result["decision"], "convention_checked")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "certified"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("not a certified color transform", result["openQuestions"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "fault": "transpose"},
            {**valid, "determinantFinite": 1},
            {**valid, "neutralVector": ""},
            {**valid, "colorVector": "bad vector"},
            {k: v for k, v in valid.items() if k != "fault"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
