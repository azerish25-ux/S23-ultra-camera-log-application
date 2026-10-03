"""TC-P033-07 source mutation during development."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p033_tc07", Path(__file__).resolve().parents[1] / "gates" / "p033_tc07.py"
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
_FORBIDDEN = {"qualified", "allowed"}
_EVIDENCE = ["source-hash", "profile-hash", "partial-read"]


def payload(**overrides):
    base = {
        "mutation": "none",
        "noticed": False,
        "published": False,
        "overwriteOriginal": False,
        "evidence": list(_EVIDENCE),
    }
    base.update(overrides)
    return base


class TcP03307(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P033-07")
        self.assertNotIn(result["decision"], _FORBIDDEN)
        self.assertTrue(result["reasons"])
        self.assertEqual(result["preservedResults"], _EVIDENCE)

    def test_repeat_mutations_stop_publication(self):
        for mutation in ("renamed", "changed-bytes", "replaced-profile", "revoked-read"):
            result = evaluate(payload(mutation=mutation, noticed=True, published=False))
            self.assertContract(result)
            self.assertEqual(result["decision"], "publication_stopped")
            self.assertNotIn(result["decision"], _FORBIDDEN | {"consistent_read"})
            self.assertIn("identity-" + mutation, result["rejectedClaims"])
            self.assertIn(_MODULE.EXPECTED, result["reasons"])
            self.assertIn("source-hash", result["preservedResults"])
            self.assertIn("profile-hash", result["preservedResults"])

    def test_negative_unnoticed_published_change_fails(self):
        result = evaluate(payload(mutation="changed-bytes", noticed=False, published=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], _FORBIDDEN | {"publication_stopped", "consistent_read"})
        self.assertIn("unnoticed-source-change", result["rejectedClaims"])
        self.assertIn("identity-changed-bytes", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertEqual(result["preservedResults"], _EVIDENCE)

    def test_overwrite_is_rejected_and_evidence_remains(self):
        result = evaluate(payload(overwriteOriginal=True, published=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["original-overwritten"])
        self.assertEqual(result["preservedResults"], _EVIDENCE)
        self.assertNotIn(result["decision"], _FORBIDDEN)

    def test_consistent_read_is_not_qualified(self):
        result = evaluate(payload(published=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "consistent_read")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertNotIn(result["decision"], _FORBIDDEN)
        self.assertTrue(any("not physical qualification" in item for item in result["reasons"]))

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "mutation": "deleted"},
            {**valid, "noticed": True},
            {**valid, "published": "yes"},
            {**valid, "evidence": []},
            {**valid, "evidence": ["source-hash", "source-hash"]},
            {**valid, "overwriteOriginal": 0},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
