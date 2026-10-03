"""TC-P037-07 source mutation during development."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p037_tc07", Path(__file__).resolve().parents[1] / "gates" / "p037_tc07.py"
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
        "sourceId": "src1",
        "profileId": "prof1",
        "sourceDigest": "aaaa",
        "observedDigest": "aaaa",
        "mutation": "none",
        "noticed": False,
        "publish": False,
    }
    base.update(overrides)
    return base


class TcP03707(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P037-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_unchanged_source_is_not_a_qualification(self):
        result = evaluate(payload(publish=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "development_read")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("sourceDigest:aaaa", result["preservedResults"])
        self.assertIn("observedDigest:aaaa", result["preservedResults"])

    def test_renamed_file_stops_publication(self):
        result = evaluate(payload(mutation="renamed", noticed=True, publish=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "publication_stopped")
        self.assertEqual(result["rejectedClaims"], ["renamed"])
        self.assertIn("source:src1", result["preservedResults"])
        self.assertIn("profile:prof1", result["preservedResults"])

    def test_changed_bytes_stop_publication(self):
        result = evaluate(
            payload(mutation="changed_bytes", observedDigest="bbbb", noticed=True, publish=True)
        )
        self.assertEqual(result["decision"], "publication_stopped")
        self.assertIn("sourceDigest:aaaa", result["preservedResults"])
        self.assertIn("observedDigest:bbbb", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_replaced_profile_and_revoked_read_stop_publication(self):
        replaced = evaluate(payload(mutation="replaced_profile", noticed=True))
        revoked = evaluate(payload(mutation="revoked_read", noticed=True, publish=True))
        self.assertEqual(replaced["decision"], "publication_stopped")
        self.assertEqual(revoked["decision"], "publication_stopped")
        self.assertEqual(replaced["rejectedClaims"], ["replaced_profile"])
        self.assertEqual(revoked["rejectedClaims"], ["revoked_read"])
        self.assertIn("source:src1", revoked["preservedResults"])

    def test_unnoticed_publish_fails(self):
        result = evaluate(
            payload(mutation="changed_bytes", observedDigest="bbbb", noticed=False, publish=True)
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "development_read", "publication_stopped"})
        self.assertIn("unnoticed-source-change", result["rejectedClaims"])
        self.assertIn("sourceDigest:aaaa", result["preservedResults"])
        self.assertIn("observedDigest:bbbb", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "mutation": "changed_bytes"},
            {**valid, "noticed": True},
            {**valid, "sourceDigest": "AA"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
