"""TC-P038-07 mutation during development stops publication."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p038_tc07", Path(__file__).resolve().parents[1] / "gates" / "p038_tc07.py"
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
_ORIGINAL = "take-fw1.raw"
_EVIDENCE = ["hash:abc", "profile:snap-fw1"]


def payload(**overrides):
    base = {
        "originalId": _ORIGINAL,
        "observedId": _ORIGINAL,
        "mutation": "none",
        "unnoticedSuccess": False,
        "evidenceTokens": list(_EVIDENCE),
    }
    base.update(overrides)
    return base


class TcP03807(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P038-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertEqual(result["preservedResults"][0], _ORIGINAL)
        self.assertIn("hash:abc", result["preservedResults"])
        self.assertIn("profile:snap-fw1", result["preservedResults"])

    def test_consistent_read_is_not_a_qualification(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "consistent")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("not a physical qualification", result["openQuestions"])

    def test_renamed_file_stops_and_keeps_both_names(self):
        result = evaluate(payload(mutation="renamed", observedId="take-fw1-renamed.raw"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "stopped")
        self.assertEqual(result["rejectedClaims"], ["renamed"])
        self.assertEqual(result["preservedResults"][0], _ORIGINAL)
        self.assertIn("observed:take-fw1-renamed.raw", result["preservedResults"])

    def test_changed_bytes_and_replaced_profile_stop_publication(self):
        for kind in ("changed-bytes", "replaced-profile"):
            result = evaluate(payload(mutation=kind))
            self.assertEqual(result["decision"], "stopped")
            self.assertIn(kind, result["rejectedClaims"])
            self.assertEqual(result["preservedResults"][0], _ORIGINAL)
            self.assertIn("accepted publication stopped", result["openQuestions"])

    def test_revoked_read_preserves_evidence(self):
        result = evaluate(payload(mutation="revoked-read"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "stopped")
        self.assertIn("revoked-read", result["rejectedClaims"])
        self.assertIn("read access revoked", result["openQuestions"])
        self.assertIn("hash:abc", result["preservedResults"])

    def test_unnoticed_success_fails(self):
        result = evaluate(payload(mutation="changed-bytes", unnoticedSuccess=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("unnoticed-source-change", result["rejectedClaims"])
        self.assertIn("changed-bytes", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertEqual(result["preservedResults"][0], _ORIGINAL)
        self.assertNotIn(result["decision"], {"qualified", "allowed", "consistent", "stopped"})

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate(payload(unnoticedSuccess=True))
        with self.assertRaises(ValueError):
            evaluate(payload(mutation="renamed", observedId=_ORIGINAL))


if __name__ == "__main__":
    unittest.main()
