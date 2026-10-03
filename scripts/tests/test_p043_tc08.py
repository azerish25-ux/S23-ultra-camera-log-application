"""TC-P043-08 profile replacement and rollback."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p043_tc08", Path(__file__).resolve().parents[1] / "gates" / "p043_tc08.py"
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
        "archiveId": "archive-1",
        "previousProfileId": "profile-v1",
        "previousRecipe": "recipe-v1",
        "nextProfileId": "profile-v2",
        "nextRecipe": "recipe-v2",
        "action": "revise",
        "rendered": True,
        "explicitNewRender": True,
    }
    base.update(overrides)
    return base


class TcP04308(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P043-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn("archive:archive-1", result["preservedResults"])
        self.assertIn("previous:profile-v1:recipe-v1", result["preservedResults"])

    def test_overwrite_same_identifier_fails(self):
        result = evaluate(
            payload(
                action="overwrite",
                nextProfileId="profile-v1",
                nextRecipe="recipe-replaced",
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "revision_recorded"})
        self.assertIn("overwrite-same-identifier", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("previous:profile-v1:recipe-v1", result["preservedResults"])
        self.assertIn("refused:profile-v1:recipe-replaced", result["preservedResults"])
        self.assertNotIn("previous:profile-v1:recipe-replaced", result["preservedResults"])

    def test_firmware_change_keeps_the_archived_recipe(self):
        result = evaluate(
            payload(action="firmware-change", nextProfileId="profile-fw2", nextRecipe="recipe-fw2")
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "revision_recorded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("previous:profile-v1:recipe-v1", result["preservedResults"])
        self.assertIn("next:profile-fw2:recipe-fw2", result["preservedResults"])
        self.assertIn("archive:archive-1", result["preservedResults"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_user_rename_keeps_both_identities(self):
        result = evaluate(payload(action="rename", nextProfileId="profile-renamed", nextRecipe="recipe-v1"))
        self.assertEqual(result["decision"], "revision_recorded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("previous:profile-v1:recipe-v1", result["preservedResults"])
        self.assertIn("next:profile-renamed:recipe-v1", result["preservedResults"])
        self.assertIn("archive:archive-1", result["preservedResults"])
        self.assertIn("new-render:rename", result["openQuestions"])

    def test_rollback_restores_the_previous_recipe(self):
        result = evaluate(
            payload(
                action="rollback",
                nextProfileId="profile-v1",
                nextRecipe="recipe-v1",
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rolled_back")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("previous:profile-v1:recipe-v1", result["preservedResults"])
        self.assertIn("archive:archive-1", result["preservedResults"])
        self.assertTrue(all(not item.startswith("next:") for item in result["preservedResults"]))

    def test_implicit_replacement_is_rejected(self):
        result = evaluate(payload(explicitNewRender=False))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("implicit-replacement", result["rejectedClaims"])
        self.assertIn("previous:profile-v1:recipe-v1", result["preservedResults"])
        self.assertIn("refused:profile-v2:recipe-v2", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "revision_recorded"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "action": "delete"},
            {**valid, "archiveId": ""},
            {**valid, "rendered": "true"},
            {**valid, "previousRecipe": " "},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
