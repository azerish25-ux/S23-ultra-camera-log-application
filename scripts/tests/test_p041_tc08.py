"""TC-P041-08 profile replacement and rollback."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p041_tc08", Path(__file__).resolve().parents[1] / "gates" / "p041_tc08.py"
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
_OLD = "a" * 64
_NEW = "b" * 64


def payload(**overrides):
    base = {
        "archivedRecipeId": "recipe-arch-1",
        "archivedProfileId": "profile-v1",
        "archivedHash": _OLD,
        "incomingProfileId": "profile-v2",
        "incomingHash": _NEW,
        "action": "install",
        "newRenderRequested": True,
        "sameIdentifierOverwrite": False,
    }
    base.update(overrides)
    return base


class TcP04108(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P041-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_same_identifier_overwrite_fails_and_keeps_the_recipe(self):
        result = evaluate(
            payload(
                incomingProfileId="profile-v1",
                incomingHash=_NEW,
                sameIdentifierOverwrite=True,
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["same-identifier-overwrite"])
        self.assertIn("recipe:recipe-arch-1", result["preservedResults"])
        self.assertIn(f"archived:profile-v1:{_OLD}", result["preservedResults"])
        self.assertIn(f"incoming:profile-v1:{_NEW}", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("historical provenance was not rewritten", result["openQuestions"])

    def test_explicit_install_preserves_the_archived_recipe(self):
        result = evaluate(payload())
        self.assertEqual(result["decision"], "explicit_rerender")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("recipe:recipe-arch-1", result["preservedResults"])
        self.assertIn(f"archived:profile-v1:{_OLD}", result["preservedResults"])
        self.assertIn(f"incoming:profile-v2:{_NEW}", result["preservedResults"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_install_without_new_render_is_withheld(self):
        result = evaluate(payload(newRenderRequested=False))
        self.assertEqual(result["decision"], "withheld")
        self.assertIn("recipe:recipe-arch-1", result["preservedResults"])
        self.assertIn("explicit new render was not requested", result["openQuestions"])

    def test_firmware_change_repeat_does_not_rewrite_history(self):
        result = evaluate(
            payload(
                action="firmware-change",
                incomingProfileId="profile-fw-2",
                archivedRecipeId="recipe-fw-1",
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "explicit_rerender")
        self.assertIn("recipe:recipe-fw-1", result["preservedResults"])
        self.assertIn(f"archived:profile-v1:{_OLD}", result["preservedResults"])
        self.assertIn("action:firmware-change", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_user_rename_repeat_keeps_the_archived_identity(self):
        result = evaluate(
            payload(
                action="rename",
                incomingProfileId="profile-renamed",
                incomingHash=_OLD,
                newRenderRequested=False,
            )
        )
        self.assertEqual(result["decision"], "renamed")
        self.assertIn("recipe:recipe-arch-1", result["preservedResults"])
        self.assertIn(f"archived:profile-v1:{_OLD}", result["preservedResults"])
        self.assertIn(f"incoming:profile-renamed:{_OLD}", result["preservedResults"])
        self.assertIn("user rename kept the archived recipe identity", result["reasons"])

    def test_rollback_repeat_restores_the_archived_hash(self):
        result = evaluate(
            payload(
                action="rollback",
                incomingProfileId="profile-v1",
                incomingHash=_OLD,
                newRenderRequested=False,
            )
        )
        self.assertEqual(result["decision"], "rolled_back")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn(f"archived:profile-v1:{_OLD}", result["preservedResults"])
        self.assertIn(f"incoming:profile-v1:{_OLD}", result["preservedResults"])
        self.assertIn("rollback restored the archived profile without rewriting it", result["reasons"])

    def test_rollback_with_different_bytes_does_not_rewrite_history(self):
        result = evaluate(
            payload(action="rollback", incomingProfileId="profile-v2", incomingHash=_NEW)
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["rollback-hash-mismatch"])
        self.assertIn(f"archived:profile-v1:{_OLD}", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "action": "delete"},
            {**valid, "archivedHash": "A" * 64},
            {**valid, "incomingHash": "abc"},
            {**valid, "archivedRecipeId": "1recipe"},
            {**valid, "newRenderRequested": "true"},
            {**valid, "sameIdentifierOverwrite": 1},
            {k: v for k, v in valid.items() if k != "action"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
