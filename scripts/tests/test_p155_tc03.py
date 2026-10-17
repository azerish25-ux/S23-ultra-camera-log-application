"""Tests for TC-P155-03."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p155_tc03",
    Path(__file__).resolve().parents[1] / "gates" / "p155_tc03.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def alt(name, tried, result):
    return {"name": name, "tried": tried, "result": result}


def payload(**overrides):
    base = _GATE.core_payload(repeat="surface input")
    base.update({"declaresAllTenBitEncodingImpossible": False})
    base.update(overrides)
    return base


class TCP15503(unittest.TestCase):
    def assert_contract(self, result, evidence="p155-reversible-alternatives"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P155-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_explored_surface_route_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertFalse(result["preservedResults"][3]["declaresAllTenBitEncodingImpossible"])
        self.assertTrue(result["preservedResults"][3]["p010Failed"])
        self.assertIn("available", result["preservedResults"][3]["results"])
        self.assertEqual(_MODULE.CASE["name"], "Unexplored reversible alternative")
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "one-failed-p010-proves-all-ten-bit-impossible")

    def test_declaring_impossible_while_a_route_is_open_is_rejected(self):
        result = evaluate(payload(declaresAllTenBitEncodingImpossible=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        by_name = {row["name"]: row for row in result["preservedResults"][1]["alternatives"]}
        self.assertEqual(by_name["surface-ten-bit-encoder"]["result"], "available")

    def test_untested_public_route_blocks_the_impossible_claim(self):
        rows = [
            alt("p010-image", True, "unavailable"),
            alt("surface-ten-bit-encoder", False, "untested"),
        ]
        result = evaluate(payload(
            alternatives=rows,
            conclusion=_GATE.UNTESTED_REMAIN,
            declaresAllTenBitEncodingImpossible=False,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        blocked = evaluate(payload(
            alternatives=rows,
            conclusion=_GATE.ALL_TEN_BIT_UNAVAILABLE,
            declaresAllTenBitEncodingImpossible=True,
        ))
        self.assertEqual(blocked["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, blocked["rejectedClaims"])
        self.assertIn(_GATE.UNTESTED_BLOCKS_ALL_UNAVAILABLE, blocked["rejectedClaims"])
        self.assertIn(_GATE.ONE_CODEC_MARKS_ALL, blocked["rejectedClaims"])
        self.assertEqual(blocked["preservedResults"][1]["alternatives"][1]["result"], "untested")

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p155-tc03-scheduling"
        result = evaluate(payload(evidenceId=evidence, repeat="scheduling changes"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(declaresAllTenBitEncodingImpossible="yes"))
