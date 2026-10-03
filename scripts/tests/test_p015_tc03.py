"""TC-P015-03 selecting every supported stream is not coexistence."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p015_tc03", Path(__file__).resolve().parents[1] / "gates" / "p015_tc03.py"
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


def outputs(*ids):
    return [{"id": item, "supportedAlone": True} for item in ids]


def payload(variant, ids, **overrides):
    base = {
        "outputs": outputs(*ids),
        "constraintsViolated": True,
        "selectAll": False,
        "variant": variant,
    }
    base.update(overrides)
    return base


class TcP01503(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P015-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_contract_text(self):
        self.assertIn("simultaneous combination", _MODULE.INTERVENTION)
        self.assertIn("coexistence", _MODULE.EXPECTED)
        self.assertIn("simultaneously must fail", _MODULE.NEGATIVE)
        self.assertIn("alternate lens", _MODULE.REPEAT)

    def test_mixed_preview_violation_keeps_each_output(self):
        ids = ["preview-1080", "preview-720"]
        result = evaluate(payload("mixed_preview", ids))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["preservedResults"], ids)
        self.assertIn("coexistence", result["rejectedClaims"])
        self.assertIn("replan required", result["openQuestions"])
        self.assertTrue(any("not coexistence" in item for item in result["reasons"]))

    def test_raw_plus_encoder_is_rejected(self):
        ids = ["raw-4000", "hevc-3840"]
        result = evaluate(payload("raw_plus_encoder", ids))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["preservedResults"], ids)
        self.assertIn("raw-4000", result["rejectedClaims"])
        self.assertIn("hevc-3840", result["rejectedClaims"])

    def test_select_all_on_alternate_lens_fails(self):
        ids = ["lens-wide", "lens-tele", "lens-front"]
        result = evaluate(
            payload("alternate_lens", ids, constraintsViolated=False, selectAll=True)
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "within_constraints"})
        self.assertEqual(result["preservedResults"], ids)
        self.assertIn("select-all", result["rejectedClaims"])
        self.assertTrue(any("simultaneously fails" in item for item in result["reasons"]))

    def test_intact_constraints_are_not_physical_proof(self):
        ids = ["preview-1080", "preview-720"]
        result = evaluate(
            payload("mixed_preview", ids, constraintsViolated=False, selectAll=False)
        )
        self.assertEqual(result["decision"], "within_constraints")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"], ids)
        self.assertEqual(result["openQuestions"], [])

    def test_invalid_payload_raises(self):
        valid = payload("mixed_preview", ["a", "b"])
        cases = [
            None,
            {},
            {**valid, "variant": "other"},
            {**valid, "outputs": [{"id": "only", "supportedAlone": True}]},
            {**valid, "selectAll": "yes"},
            {**valid, "constraintsViolated": 1},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
