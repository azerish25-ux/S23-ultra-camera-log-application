"""TC-P039-07 source mutation during development."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p039_tc07", Path(__file__).resolve().parents[1] / "gates" / "p039_tc07.py"
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
        "sourceId": "raw-take-1",
        "profileId": "profile-capture",
        "sourceDigest": "abcd",
        "observedDigest": "abcd",
        "mutation": "none",
        "noticed": False,
        "publish": False,
    }
    base.update(overrides)
    return base


class TcP03907(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P039-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def assert_evidence(self, result, observed="abcd"):
        self.assertIn("source:raw-take-1", result["preservedResults"])
        self.assertIn("profile:profile-capture", result["preservedResults"])
        self.assertIn("sourceDigest:abcd", result["preservedResults"])
        self.assertIn(f"observedDigest:{observed}", result["preservedResults"])

    def test_unchanged_read_is_not_qualification(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "development_read")
        self.assertEqual(result["rejectedClaims"], [])
        self.assert_evidence(result)

    def test_renamed_file_stops_publication(self):
        result = evaluate(payload(mutation="renamed", noticed=True, publish=False))
        self.assertEqual(result["decision"], "publication_stopped")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("renamed", result["rejectedClaims"])
        self.assert_evidence(result)
        self.assertIn("renamed detected", result["openQuestions"])

    def test_changed_bytes_stop_publication(self):
        result = evaluate(
            payload(
                mutation="changed_bytes",
                observedDigest="abce",
                noticed=True,
                publish=False,
            )
        )
        self.assertEqual(result["decision"], "publication_stopped")
        self.assertIn("changed_bytes", result["rejectedClaims"])
        self.assert_evidence(result, "abce")

    def test_replaced_profile_and_revoked_read_stop_publication(self):
        replaced = evaluate(payload(mutation="replaced_profile", noticed=True))
        self.assertEqual(replaced["decision"], "publication_stopped")
        self.assertIn("replaced_profile", replaced["rejectedClaims"])
        self.assert_evidence(replaced)
        revoked = evaluate(payload(mutation="revoked_read", noticed=True))
        self.assertEqual(revoked["decision"], "publication_stopped")
        self.assertIn("revoked_read", revoked["rejectedClaims"])
        self.assert_evidence(revoked)

    def test_unnoticed_success_negative_is_rejected(self):
        result = evaluate(
            payload(
                mutation="changed_bytes",
                observedDigest="abce",
                noticed=False,
                publish=True,
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("unnoticed-source-change", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assert_evidence(result, "abce")


if __name__ == "__main__":
    unittest.main()
