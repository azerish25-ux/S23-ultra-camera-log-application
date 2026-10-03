"""TC-P040-07 source mutation during development."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p040_tc07", Path(__file__).resolve().parents[1] / "gates" / "p040_tc07.py"
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
_EVIDENCE = ["source-bytes", "profile-bytes"]


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


class TcP04007(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P040-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertEqual(result["preservedResults"], _EVIDENCE)

    def test_intervention_expected_and_negative_are_encoded(self):
        self.assertIn("development job", _MODULE.INTERVENTION)
        self.assertIn("stop accepted publication", _MODULE.EXPECTED)
        self.assertIn("changed unnoticed", _MODULE.NEGATIVE)

    def test_consistent_read_is_not_a_qualified_publication(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "consistent")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(any("not a qualified publication" in item for item in result["reasons"]))

    def test_renamed_file_stops_publication_and_keeps_evidence(self):
        result = evaluate(payload(mutation="renamed", noticed=True, published=False))
        self.assertContract(result)
        self.assertEqual(result["decision"], "stopped")
        self.assertEqual(result["rejectedClaims"], ["renamed"])
        self.assertEqual(result["preservedResults"], _EVIDENCE)
        self.assertIn("publication stopped", result["openQuestions"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_changed_bytes_stop_publication(self):
        result = evaluate(payload(mutation="changed_bytes"))
        self.assertEqual(result["decision"], "stopped")
        self.assertEqual(result["rejectedClaims"], ["changed_bytes"])
        self.assertEqual(result["preservedResults"], _EVIDENCE)

    def test_replaced_profile_stops_publication(self):
        result = evaluate(payload(mutation="replaced_profile"))
        self.assertEqual(result["decision"], "stopped")
        self.assertEqual(result["rejectedClaims"], ["replaced_profile"])
        self.assertIn("profile-bytes", result["preservedResults"])

    def test_revoked_read_stops_publication(self):
        result = evaluate(payload(mutation="revoked_read"))
        self.assertEqual(result["decision"], "stopped")
        self.assertEqual(result["rejectedClaims"], ["revoked_read"])
        self.assertEqual(result["preservedResults"], _EVIDENCE)
        self.assertIn("identity inconsistency revoked_read detected", result["reasons"])

    def test_negative_unnoticed_success_fails(self):
        result = evaluate(payload(mutation="changed_bytes", noticed=False, published=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "consistent", "stopped"})
        self.assertIn("unnoticed-source-change", result["rejectedClaims"])
        self.assertIn("published-after-mutation", result["rejectedClaims"])
        self.assertIn("changed_bytes", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"], _EVIDENCE)
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("evidence preserved", result["openQuestions"])

    def test_overwrite_original_is_rejected_without_losing_evidence(self):
        result = evaluate(payload(mutation="renamed", overwriteOriginal=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("overwrite-original", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"], _EVIDENCE)
        self.assertIn("originals were not overwritten", result["reasons"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "evidence"},
            {**valid, "extra": True},
            {**valid, "mutation": "deleted"},
            {**valid, "evidence": []},
            {**valid, "evidence": ["a", "a"]},
            {**valid, "noticed": "yes"},
            {**valid, "published": 1},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
