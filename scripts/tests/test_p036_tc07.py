"""TC-P036-07 source mutation during development."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p036_tc07", Path(__file__).resolve().parents[1] / "gates" / "p036_tc07.py"
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
_EVIDENCE = ["source-bytes", "profile-id", "read-log"]


def payload(**overrides):
    base = {
        "mutation": "none",
        "noticed": True,
        "published": False,
        "overwriteOriginal": False,
        "evidence": list(_EVIDENCE),
    }
    base.update(overrides)
    return base


class TcP03607(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P036-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertEqual(result["preservedResults"], _EVIDENCE)

    def test_renamed_file_stops_publication_and_keeps_evidence(self):
        result = evaluate(payload(mutation="renamed", noticed=True, published=False))
        self.assertContract(result)
        self.assertEqual(result["decision"], "stopped")
        self.assertEqual(result["rejectedClaims"], ["renamed"])
        self.assertIn("publication stopped", result["openQuestions"])

    def test_changed_bytes_stop_publication(self):
        result = evaluate(payload(mutation="changed_bytes", noticed=True))
        self.assertEqual(result["decision"], "stopped")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("changed_bytes", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"], _EVIDENCE)

    def test_replaced_profile_stops_publication(self):
        result = evaluate(payload(mutation="replaced_profile", noticed=True))
        self.assertEqual(result["decision"], "stopped")
        self.assertIn("replaced_profile", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"], _EVIDENCE)

    def test_revoked_read_stops_publication(self):
        result = evaluate(payload(mutation="revoked_read", noticed=True))
        self.assertEqual(result["decision"], "stopped")
        self.assertIn("revoked_read", result["rejectedClaims"])
        self.assertIn("source-bytes", result["preservedResults"])

    def test_negative_unnoticed_change_is_not_successful(self):
        result = evaluate(payload(mutation="changed_bytes", noticed=False, published=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "consistent", "stopped"})
        self.assertIn("unnoticed-source-change", result["rejectedClaims"])
        self.assertIn("published-after-mutation", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"], _EVIDENCE)
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_overwrite_does_not_drop_original_evidence(self):
        result = evaluate(payload(mutation="renamed", noticed=True, overwriteOriginal=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("overwrite-original", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"], _EVIDENCE)

    def test_consistent_read_is_not_qualified(self):
        result = evaluate(payload())
        self.assertEqual(result["decision"], "consistent")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["preservedResults"], _EVIDENCE)
        self.assertEqual(result["rejectedClaims"], [])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "mutation": "deleted"},
            {**valid, "evidence": []},
            {**valid, "noticed": "yes"},
            {**valid, "evidence": ["source-bytes", "source-bytes"]},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
