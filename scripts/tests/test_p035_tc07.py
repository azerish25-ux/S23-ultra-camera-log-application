"""TC-P035-07 source mutation during development."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p035_tc07", Path(__file__).resolve().parents[1] / "gates" / "p035_tc07.py"
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
        "mutation": "changed_bytes",
        "sourceBefore": "sha:aaa",
        "sourceDuring": "sha:bbb",
        "profileBefore": "sha:ppp",
        "profileDuring": "sha:ppp",
        "nameBefore": "take.s23raw",
        "nameDuring": "take.s23raw",
        "publish": True,
        "noticed": True,
    }
    base.update(overrides)
    return base


class TcP03507(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P035-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_repeat_renamed_file_stops_publication(self):
        result = evaluate(
            payload(
                mutation="renamed",
                sourceBefore="sha:aaa",
                sourceDuring="sha:aaa",
                nameDuring="take-renamed.s23raw",
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "stopped")
        self.assertIn("publication-blocked", result["rejectedClaims"])
        self.assertIn("name-before:take.s23raw", result["preservedResults"])
        self.assertIn("name-during:take-renamed.s23raw", result["preservedResults"])
        self.assertIn("source-before:sha:aaa", result["preservedResults"])

    def test_repeat_changed_bytes(self):
        result = evaluate(payload(mutation="changed_bytes"))
        self.assertEqual(result["decision"], "stopped")
        self.assertIn("source-before:sha:aaa", result["preservedResults"])
        self.assertIn("source-during:sha:bbb", result["preservedResults"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_repeat_replaced_profile_and_revoked_read(self):
        profile = evaluate(
            payload(
                mutation="replaced_profile",
                sourceDuring="sha:aaa",
                profileDuring="sha:qqq",
                publish=False,
            )
        )
        revoked = evaluate(
            payload(mutation="revoked_read", sourceDuring="sha:aaa", publish=False)
        )
        self.assertEqual(profile["decision"], "stopped")
        self.assertEqual(profile["rejectedClaims"], [])
        self.assertIn("profile-before:sha:ppp", profile["preservedResults"])
        self.assertIn("profile-during:sha:qqq", profile["preservedResults"])
        self.assertEqual(revoked["decision"], "stopped")
        self.assertIn("source-before:sha:aaa", revoked["preservedResults"])
        self.assertNotIn(revoked["decision"], {"qualified", "allowed"})

    def test_negative_unnoticed_change_is_not_success(self):
        result = evaluate(payload(noticed=False, publish=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["unnoticed-mutation"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("source-before:sha:aaa", result["preservedResults"])
        self.assertIn("source-during:sha:bbb", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "consistent"})

    def test_unchanged_identity_is_not_qualification(self):
        result = evaluate(
            payload(
                mutation="none",
                sourceDuring="sha:aaa",
                profileDuring="sha:ppp",
                nameDuring="take.s23raw",
                publish=False,
            )
        )
        self.assertEqual(result["decision"], "consistent")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("source-before:sha:aaa", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "mutation": "none"},
            {**valid, "mutation": "renamed"},
            {**valid, "noticed": "yes"},
            {**valid, "sourceBefore": ""},
            {key: value for key, value in valid.items() if key != "publish"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
