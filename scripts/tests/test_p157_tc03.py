"""Tests for TC-P157-03."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p157_tc03",
    Path(__file__).resolve().parents[1] / "gates" / "p157_tc03.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def routes(**overrides):
    rows = [
        {"id": "p010", "tested": True, "failed": True, "reversible": True, "tenBit": True},
        {"id": "surface-input", "tested": True, "failed": False, "reversible": True, "tenBit": True},
        {"id": "reduced-geometry", "tested": True, "failed": False, "reversible": True, "tenBit": False},
        {"id": "deferred-processing", "tested": True, "failed": False, "reversible": True, "tenBit": False},
        {"id": "scheduling", "tested": True, "failed": False, "reversible": True, "tenBit": False},
    ]
    by_id = {row["id"]: row for row in rows}
    for route_id, fields in overrides.items():
        by_id[route_id].update(fields)
    return list(by_id.values())


def payload(**overrides):
    base = _GATE.core_payload()
    base.update({
        "repeat": "surface input",
        "routes": routes(),
        "broaderCaptureGoalBlocked": False,
        "tenBitDeclaredImpossible": False,
    })
    base.update(overrides)
    if "experiments" in overrides and "checksum" not in overrides:
        base["checksum"] = _GATE.protocol_checksum(base["experiments"])
    return base


class TCP15703(unittest.TestCase):
    def assert_contract(self, result, evidence="p157-instrumented-experiment-design"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P157-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_failed_p010_with_open_alternatives_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][3]["failedRoutes"], ["p010"])
        self.assertEqual(_MODULE.CASE["name"], "Unexplored reversible alternative")
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "one-p010-failure-blocks-all-ten-bit")

    def test_one_p010_failure_does_not_make_ten_bit_impossible(self):
        result = evaluate(payload(tenBitDeclaredImpossible=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_blocking_the_goal_while_a_route_is_untested_is_rejected(self):
        result = evaluate(payload(
            routes=routes(**{"surface-input": {"tested": False, "failed": False}}),
            broaderCaptureGoalBlocked=True,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.UNTESTED_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["expected"], result["reasons"])

    def test_blocking_the_goal_after_a_successful_alternative_is_rejected(self):
        result = evaluate(payload(broaderCaptureGoalBlocked=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.OPEN_ALTERNATIVE_TOKEN, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p157-tc03-scheduling"
        result = evaluate(payload(evidenceId=evidence, repeat="scheduling changes"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(routes=routes(**{"p010": {"tested": False, "failed": True}})))
