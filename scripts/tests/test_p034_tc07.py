"""TC-P034-07 source mutation during development."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p034_tc07", Path(__file__).resolve().parents[1] / "gates" / "p034_tc07.py"
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
        "noticed": True,
        "originalId": "src-1",
        "evidence": ["hash:abc", "profile:p1"],
    }
    base.update(overrides)
    return base


class TcP03407(unittest.TestCase):
    def assert_contract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P034-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("original:src-1", result["preservedResults"])
        self.assertIn("evidence:hash:abc", result["preservedResults"])
        self.assertIn("evidence:profile:p1", result["preservedResults"])
        self.assertTrue(result["reasons"])

    def test_module_encodes_case_text(self):
        self.assertIn("development job", _MODULE.INTERVENTION)
        self.assertIn("stop accepted publication", _MODULE.EXPECTED)
        self.assertIn("source changed unnoticed", _MODULE.NEGATIVE)

    def test_renamed_file_stops_publication(self):
        result = evaluate(payload(mutation="renamed"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "publication_stopped")
        self.assertEqual(result["openQuestions"], ["stopped:renamed"])
        self.assertEqual(result["rejectedClaims"], [])

    def test_changed_bytes_stops_publication(self):
        result = evaluate(payload(mutation="changed_bytes"))
        self.assertEqual(result["decision"], "publication_stopped")
        self.assertIn("original:src-1", result["preservedResults"])
        self.assertIn("evidence:hash:abc", result["preservedResults"])

    def test_replaced_profile_stops_publication(self):
        result = evaluate(payload(mutation="replaced_profile"))
        self.assertEqual(result["decision"], "publication_stopped")
        self.assertEqual(result["openQuestions"], ["stopped:replaced_profile"])
        self.assertIn("evidence:profile:p1", result["preservedResults"])

    def test_revoked_read_stops_publication(self):
        result = evaluate(payload(mutation="revoked_read"))
        self.assertEqual(result["decision"], "publication_stopped")
        self.assertIn("original:src-1", result["preservedResults"])
        self.assertEqual(result["openQuestions"], ["stopped:revoked_read"])

    def test_negative_unnoticed_change_is_not_success(self):
        result = evaluate(payload(mutation="changed_bytes", noticed=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "consistent", "publication_stopped"})
        self.assertEqual(result["rejectedClaims"], ["unnoticed-mutation:changed_bytes"])
        self.assertIn("original:src-1", result["preservedResults"])
        self.assertIn("evidence:hash:abc", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_unchanged_source_is_not_qualification(self):
        result = evaluate(payload(mutation="none", noticed=True))
        self.assertEqual(result["decision"], "consistent")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("original:src-1", result["preservedResults"])
        self.assertIn("physical development unverified", result["openQuestions"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate(payload(mutation="none", noticed=False))
        with self.assertRaises(ValueError):
            evaluate(payload(evidence=[]))


if __name__ == "__main__":
    unittest.main()
