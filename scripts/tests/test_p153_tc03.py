"""Tests for TC-P153-03."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p153_tc03",
    Path(__file__).resolve().parents[1] / "gates" / "p153_tc03.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    return _MODULE.example_payload(**overrides)


class TCP15303(unittest.TestCase):
    def assert_contract(self, result, evidence="p153-blocked-capability"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P153-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_narrow_p010_failure_does_not_block_ten_bit(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][3]["declared_blocked"], "p010")
        self.assertFalse(result["preservedResults"][3]["broaderGoal"])
        self.assertEqual(_MODULE.CASE["name"], "Unexplored reversible alternative")

    def test_one_failed_p010_route_is_not_all_ten_bit(self):
        result = evaluate(payload(declared_blocked="ten-bit-encoding", alternatives_evaluated=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.ONE_ROUTE, result["rejectedClaims"])
        self.assertIn(_MODULE.P010_NOT_ALL, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_evaluated_alternatives_can_record_a_broader_block(self):
        result = evaluate(payload(
            declared_blocked="ten-bit-encoding",
            untested_routes=[],
            alternatives_evaluated=True,
        ))
        self.assertEqual(result["decision"], "recorded")
        self.assertNotIn(_MODULE.P010_NOT_ALL, result["rejectedClaims"])
        self.assertTrue(result["preservedResults"][3]["broaderGoal"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p153-tc03-geometry"
        result = evaluate(payload(evidenceId=evidence, repeat="reduced-geometry"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(untested_routes=["p010"]))
