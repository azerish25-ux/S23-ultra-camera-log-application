"""TC-P046-08 profile replacement and rollback."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p046_tc08", Path(__file__).resolve().parents[1] / "gates" / "p046_tc08.py"
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
        "archivedId": "profile-a",
        "archivedDigest": "aaaaaaaa",
        "archivedRecipe": "recipe-v1",
        "installedId": "profile-b",
        "installedDigest": "bbbbbbbb",
        "overwriteSameId": False,
        "action": "install",
        "previousApprovedId": "profile-a",
    }
    base.update(overrides)
    return base


class TcP04608(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P046-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_new_install_keeps_the_archived_recipe(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "provenance_kept")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("archived:profile-a:aaaaaaaa", result["preservedResults"])
        self.assertIn("recipe:recipe-v1", result["preservedResults"])
        self.assertIn("installed:profile-b:bbbbbbbb", result["preservedResults"])
        self.assertIn("historical provenance", _MODULE.EXPECTED)

    def test_firmware_change_repeat_uses_a_new_identifier(self):
        result = evaluate(payload(action="firmware", installedId="profile-fw", installedDigest="cccccccc"))
        self.assertEqual(result["decision"], "provenance_kept")
        self.assertIn("action:firmware", result["preservedResults"])
        self.assertIn("recipe:recipe-v1", result["preservedResults"])
        self.assertIn("archived:profile-a:aaaaaaaa", result["preservedResults"])
        self.assertIn("installed:profile-fw:cccccccc", result["preservedResults"])

    def test_user_rename_repeat_does_not_rewrite_the_archive(self):
        result = evaluate(payload(action="rename", installedId="profile-renamed", installedDigest="dddddddd"))
        self.assertEqual(result["decision"], "provenance_kept")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("action:rename", result["preservedResults"])
        self.assertIn("recipe:recipe-v1", result["preservedResults"])
        self.assertIn("installed:profile-renamed:dddddddd", result["preservedResults"])

    def test_rollback_repeat_restores_the_previous_profile(self):
        result = evaluate(
            payload(
                action="rollback",
                installedId="profile-a",
                installedDigest="aaaaaaaa",
                previousApprovedId="profile-a",
            )
        )
        self.assertEqual(result["decision"], "rolled_back")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("recipe:recipe-v1", result["preservedResults"])
        self.assertIn("archived:profile-a:aaaaaaaa", result["preservedResults"])
        self.assertIn("previous:profile-a", result["preservedResults"])

    def test_same_identifier_overwrite_fails(self):
        result = evaluate(
            payload(
                installedId="profile-a",
                installedDigest="bbbbbbbb",
                overwriteSameId=True,
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "provenance_kept"})
        self.assertEqual(result["rejectedClaims"], ["same-identifier-overwrite"])
        self.assertIn("archived:profile-a:aaaaaaaa", result["preservedResults"])
        self.assertIn("recipe:recipe-v1", result["preservedResults"])
        self.assertIn("installed:profile-a:bbbbbbbb", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("historical provenance was not rewritten", result["openQuestions"])

    def test_digest_change_under_the_same_id_fails_without_the_flag(self):
        result = evaluate(payload(installedId="profile-a", installedDigest="eeeeeeee", action="firmware"))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["same-identifier-overwrite"])
        self.assertIn("recipe:recipe-v1", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "action"},
            {**valid, "extra": True},
            {**valid, "action": "delete"},
            {**valid, "archivedDigest": "AAAAAAA"},
            {**valid, "archivedDigest": "aaaaaaaaaa"},
            {**valid, "overwriteSameId": "false"},
            {**valid, "archivedId": "Profile-A"},
            {**valid, "archivedRecipe": "recipe v1"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
