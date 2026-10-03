"""TC-P045-08 profile replacement and rollback."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p045_tc08", Path(__file__).resolve().parents[1] / "gates" / "p045_tc08.py"
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
        "archivedRecipeId": "recipe-v1",
        "newProfileId": "profile-v2",
        "archivedBytes": "aa11",
        "newBytes": "bb22",
        "overwriteSameId": False,
        "firmwareChanged": False,
        "userRename": False,
        "rollback": False,
    }
    base.update(overrides)
    return base


class TcP04508(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P045-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn("archived:recipe-v1", result["preservedResults"])
        self.assertIn("archived-bytes:aa11", result["preservedResults"])

    def test_explicit_new_render_keeps_the_archived_recipe(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "explicit_render")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("new:profile-v2", result["preservedResults"])
        self.assertIn("new-bytes:bb22", result["preservedResults"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_negative_same_identifier_overwrite_fails(self):
        result = evaluate(
            payload(newProfileId="recipe-v1", newBytes="cc33", overwriteSameId=True)
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["same-identifier-overwrite"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("archived-bytes:aa11", result["preservedResults"])
        self.assertIn("new-bytes:cc33", result["preservedResults"])
        self.assertNotIn("archived-bytes:cc33", result["preservedResults"])

    def test_overwrite_flag_fails_even_when_ids_differ(self):
        result = evaluate(payload(overwriteSameId=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("same-identifier-overwrite", result["rejectedClaims"])
        self.assertIn("archived:recipe-v1", result["preservedResults"])
        self.assertIn("new:profile-v2", result["preservedResults"])

    def test_equal_ids_without_the_flag_still_fail(self):
        result = evaluate(payload(newProfileId="recipe-v1"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("archived-bytes:aa11", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "explicit_render"})

    def test_repeat_firmware_change(self):
        result = evaluate(payload(newProfileId="profile-fw2", firmwareChanged=True, newBytes="dd44"))
        self.assertEqual(result["decision"], "explicit_render")
        self.assertIn("archived:recipe-v1", result["preservedResults"])
        self.assertIn("new:profile-fw2", result["preservedResults"])
        self.assertTrue(any("firmware change uses a distinct profile id" in item for item in result["reasons"]))

    def test_repeat_user_rename(self):
        result = evaluate(payload(newProfileId="recipe-v1-renamed", userRename=True, newBytes="ee55"))
        self.assertEqual(result["decision"], "explicit_render")
        self.assertIn("archived:recipe-v1", result["preservedResults"])
        self.assertIn("new:recipe-v1-renamed", result["preservedResults"])
        self.assertTrue(any("user rename does not rewrite" in item for item in result["reasons"]))

    def test_repeat_rollback_to_previous_profile(self):
        result = evaluate(payload(newProfileId="profile-v0", newBytes="aa00", rollback=True))
        self.assertEqual(result["decision"], "rolled_back")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("archived:recipe-v1", result["preservedResults"])
        self.assertIn("archived-bytes:aa11", result["preservedResults"])
        self.assertIn("new:profile-v0", result["preservedResults"])
        self.assertTrue(any("rollback keeps the earlier recipe identity" in item for item in result["reasons"]))

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "archivedBytes"},
            {**valid, "extra": True},
            {**valid, "archivedBytes": "AA11"},
            {**valid, "newBytes": "zz"},
            {**valid, "overwriteSameId": "false"},
            {**valid, "rollback": 1},
            {**valid, "archivedRecipeId": "recipe v1"},
            {**valid, "firmwareChanged": None},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
