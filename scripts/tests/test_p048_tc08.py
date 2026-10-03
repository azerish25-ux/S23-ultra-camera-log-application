"""TC-P048-08 same-identifier profile replacement fails."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p048_tc08", Path(__file__).resolve().parents[1] / "gates" / "p048_tc08.py"
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
        "profileId": "prof-v1",
        "revisedId": "prof-v2",
        "priorBytes": "bytes-v1",
        "nextBytes": "bytes-v2",
        "recipeId": "recipe-archived",
        "event": "install",
        "overwriteSameId": False,
    }
    base.update(overrides)
    return base


class TcP04808(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P048-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn("recipe:recipe-archived", result["preservedResults"])
        self.assertIn("prior-bytes:bytes-v1", result["preservedResults"])

    def test_constants(self):
        self.assertIn("revised profile", _MODULE.INTERVENTION)
        self.assertIn("earlier recipe identity", _MODULE.EXPECTED)
        self.assertIn("same identifier", _MODULE.NEGATIVE)

    def test_negative_overwrite_same_identifier_is_rejected(self):
        result = evaluate(
            payload(
                overwriteSameId=True,
                revisedId="prof-v1",
                nextBytes="bytes-replaced",
                event="install",
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("same-identifier-overwrite", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("next-bytes:bytes-replaced", result["preservedResults"])
        self.assertNotIn("revised-id:prof-v1", result["preservedResults"])

    def test_install_keeps_the_archived_recipe(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "new_development")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("revised-id:prof-v2", result["preservedResults"])
        self.assertIn("event:install", result["preservedResults"])

    def test_repeat_firmware_change_keeps_recipe(self):
        result = evaluate(payload(event="firmware", revisedId="prof-fw2", nextBytes="bytes-fw"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "versioned")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("recipe:recipe-archived", result["preservedResults"])
        self.assertIn("revised-id:prof-fw2", result["preservedResults"])
        self.assertIn("prior-bytes:bytes-v1", result["preservedResults"])

    def test_repeat_user_rename_keeps_recipe(self):
        result = evaluate(payload(event="rename", revisedId="prof-renamed", nextBytes="bytes-v1"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "renamed")
        self.assertIn("recipe:recipe-archived", result["preservedResults"])
        self.assertIn("revised-id:prof-renamed", result["preservedResults"])
        self.assertIn("profile:prof-v1", result["preservedResults"])

    def test_repeat_rollback_to_previous_approved_profile(self):
        result = evaluate(
            payload(
                event="rollback",
                revisedId="prof-v1",
                nextBytes="bytes-v1",
                priorBytes="bytes-v1",
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rolled_back")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("approved:prof-v1", result["preservedResults"])
        self.assertIn("recipe:recipe-archived", result["preservedResults"])
        self.assertEqual(result["rejectedClaims"], [])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = (
            None,
            {},
            {**valid, "event": "delete"},
            {**valid, "overwriteSameId": True},
            {**valid, "event": "rollback", "revisedId": "prof-v2"},
            {**valid, "revisedId": "prof-v1"},
        )
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
