"""TC-P042-08 profile replacement and rollback."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p042_tc08", Path(__file__).resolve().parents[1] / "gates" / "p042_tc08.py"
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
_PRIOR = "aaaabbbbccccdddd"
_NEW = "1111222233334444"


def payload(**overrides):
    base = {
        "profileId": "profile-a",
        "priorDigest": _PRIOR,
        "newDigest": _NEW,
        "archivedRecipeId": "recipe-1",
        "operation": "overwrite_same_id",
        "renameTo": None,
    }
    base.update(overrides)
    return base


class TcP04208(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P042-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn("archived", _MODULE.INTERVENTION)
        self.assertIn("earlier recipe", _MODULE.EXPECTED)
        self.assertEqual(
            _MODULE.NEGATIVE,
            "Overwriting profile bytes under the same identifier must fail.",
        )

    def test_overwrite_same_identifier_is_rejected(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["same-identifier-overwrite"])
        self.assertIn("recipe:recipe-1", result["preservedResults"])
        self.assertIn(f"prior:{_PRIOR}", result["preservedResults"])
        self.assertIn(f"proposed:{_NEW}", result["preservedResults"])
        self.assertIn("profile:profile-a", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertNotIn(f"prior:{_NEW}", result["preservedResults"])

    def test_revise_preserves_the_archived_recipe(self):
        result = evaluate(payload(operation="revise"))
        self.assertEqual(result["decision"], "explicit_rerender")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("recipe:recipe-1", result["preservedResults"])
        self.assertIn(f"prior:{_PRIOR}", result["preservedResults"])
        self.assertIn(f"proposed:{_NEW}", result["preservedResults"])
        self.assertIn("the archived recipe still names the prior digest", result["openQuestions"])

    def test_repeat_firmware_change_does_not_rewrite_history(self):
        result = evaluate(payload(operation="firmware_change"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "explicit_rerender")
        self.assertIn("operation firmware_change", result["reasons"])
        self.assertIn("recipe:recipe-1", result["preservedResults"])
        self.assertIn(f"prior:{_PRIOR}", result["preservedResults"])

    def test_repeat_rollback_restores_the_prior_digest(self):
        result = evaluate(payload(operation="rollback"))
        self.assertEqual(result["decision"], "rolled_back")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "rejected"})
        self.assertIn(f"prior:{_PRIOR}", result["preservedResults"])
        self.assertIn(f"proposed:{_NEW}", result["preservedResults"])
        self.assertIn("recipe:recipe-1", result["preservedResults"])
        self.assertIn("rollback restores the prior digest without rewriting history", result["reasons"])

    def test_user_rename_does_not_replace_the_archived_id(self):
        result = evaluate(payload(operation="user_rename", renameTo="profile-pretty"))
        self.assertEqual(result["decision"], "provenance_kept")
        self.assertIn("recipe:recipe-1", result["preservedResults"])
        self.assertIn("rename:profile-pretty", result["preservedResults"])
        self.assertIn("profile:profile-a", result["preservedResults"])
        self.assertNotIn("recipe:profile-pretty", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "priorDigest": "ABC"},
            {**valid, "operation": "delete"},
            {**valid, "renameTo": "other"},
            {**valid, "operation": "user_rename", "renameTo": None},
            {**valid, "newDigest": "zzzzzzzz"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
