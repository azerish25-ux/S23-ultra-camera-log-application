"""Tests for TC-P155-01."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p155_tc01",
    Path(__file__).resolve().parents[1] / "gates" / "p155_tc01.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def stages():
    return [
        {"name": "acquisition-only", "slow": False, "cause": "none"},
        {"name": "saved-source", "slow": True, "cause": "storage"},
        {"name": "development", "slow": False, "cause": "none"},
        {"name": "encoder-stage", "slow": True, "cause": "scheduling"},
    ]


def payload(**overrides):
    base = _GATE.core_payload(repeat="acquisition-only")
    base.update({
        "stages": stages(),
        "attribution": "isolated",
        "lowLevelModificationProposed": False,
    })
    base.update(overrides)
    return base


class TCP15501(unittest.TestCase):
    def assert_contract(self, result, evidence="p155-reversible-alternatives"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P155-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_isolated_storage_and_scheduling_are_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][3]["attribution"], "isolated")
        self.assertEqual(_MODULE.CASE["name"], "Wrong bottleneck attribution")
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "slow-path-assumed-vendor-blocking")

    def test_vendor_blocking_attribution_for_storage_is_rejected(self):
        result = evaluate(payload(attribution="vendor-blocking"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_low_level_modification_before_isolation_is_rejected(self):
        result = evaluate(payload(lowLevelModificationProposed=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.BOTTLENECK_NOT_ISOLATED, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_untested_alternative_still_rejects_the_all_unavailable_conclusion(self):
        result = evaluate(payload(conclusion=_GATE.ALL_TEN_BIT_UNAVAILABLE))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.UNTESTED_BLOCKS_ALL_UNAVAILABLE, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p155-tc01-encoder"
        result = evaluate(payload(evidenceId=evidence, repeat="encoder-stage"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(stages=[]))
        with self.assertRaises(ValueError):
            evaluate(payload(attribution="firmware"))
