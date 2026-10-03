"""TC-P047-08 profile replacement must not overwrite the archived identifier."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p047_tc08", Path(__file__).resolve().parents[1] / "gates" / "p047_tc08.py"
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
_RECIPE = "recipe:profile-v1:aaaa1111"


def payload(**overrides):
    base = {
        "archivedProfileId": "profile-v1",
        "archivedDigest": "aaaa1111",
        "installedProfileId": "profile-v2",
        "installedDigest": "bbbb2222",
        "overwriteSameId": False,
        "operation": "install",
        "rewritesHistory": False,
        "renderedResultId": "render-1",
    }
    base.update(overrides)
    return base


class TcP04708(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P047-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn(_RECIPE, result["preservedResults"])
        self.assertIn("rendered:render-1", result["preservedResults"])

    def test_constants(self):
        self.assertIn("rendered and archived", _MODULE.INTERVENTION)
        self.assertIn("historical provenance", _MODULE.EXPECTED)
        self.assertIn("same identifier", _MODULE.NEGATIVE)

    def test_explicit_install_keeps_the_archived_recipe(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "explicit_render")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("candidate:profile-v2:bbbb2222", result["preservedResults"])
        self.assertIn("operation:install", result["preservedResults"])
        self.assertNotIn("recipe:profile-v1:bbbb2222", result["preservedResults"])

    def test_same_identifier_overwrite_fails(self):
        result = evaluate(
            payload(
                installedProfileId="profile-v1",
                installedDigest="bbbb2222",
                overwriteSameId=True,
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("same-identifier-overwrite", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn(_RECIPE, result["preservedResults"])
        self.assertIn("candidate:profile-v1:bbbb2222", result["preservedResults"])
        self.assertNotIn("recipe:profile-v1:bbbb2222", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "explicit_render"})

    def test_firmware_change_repeat(self):
        result = evaluate(
            payload(
                operation="firmware-change",
                installedProfileId="profile-fw2",
                installedDigest="cccc3333",
            )
        )
        self.assertEqual(result["decision"], "explicit_render")
        self.assertIn(_RECIPE, result["preservedResults"])
        self.assertIn("operation:firmware-change", result["preservedResults"])
        self.assertIn("candidate:profile-fw2:cccc3333", result["preservedResults"])
        self.assertIn("historical provenance was not rewritten", result["reasons"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_user_rename_repeat(self):
        result = evaluate(
            payload(
                operation="user-rename",
                installedProfileId="profile-renamed",
                installedDigest="dddd4444",
            )
        )
        self.assertEqual(result["decision"], "renamed")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn(_RECIPE, result["preservedResults"])
        self.assertIn("rendered:render-1", result["preservedResults"])
        self.assertIn("user rename kept the archived recipe identity", result["reasons"])

    def test_rollback_repeat(self):
        result = evaluate(
            payload(
                operation="rollback",
                installedProfileId="profile-v1",
                installedDigest="aaaa1111",
            )
        )
        self.assertEqual(result["decision"], "rolled_back")
        self.assertIn(_RECIPE, result["preservedResults"])
        self.assertIn("candidate:profile-v1:aaaa1111", result["preservedResults"])
        self.assertIn("rollback restored the previous approved profile", result["reasons"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_history_rewrite_fails(self):
        result = evaluate(payload(rewritesHistory=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["historical-provenance-rewrite"])
        self.assertIn(_RECIPE, result["preservedResults"])
        self.assertIn("rendered:render-1", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "operation": "delete"},
            {**valid, "archivedDigest": "AAAA1111"},
            {**valid, "overwriteSameId": "false"},
            {**valid, "operation": "rollback"},
            {**valid, "operation": "user-rename", "installedProfileId": "profile-v1", "installedDigest": "aaaa1111"},
            {k: v for k, v in valid.items() if k != "renderedResultId"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
