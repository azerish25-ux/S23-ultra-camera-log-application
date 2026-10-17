"""Tests for TC-P137-03."""

from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p137_tc03",
    Path(__file__).resolve().parents[1] / "gates" / "p137_tc03.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def with_controls(record, aperture="T2.8", grade="neutral", grain="fine"):
    clone = copy.deepcopy(record)
    clone["fields"].extend([
        _GATE.make_field("virtual_aperture", "reconstruction", aperture),
        _GATE.make_field("grade", "reconstruction", grade),
        _GATE.make_field("grain", "reconstruction", grain),
    ])
    return clone


def payload(**overrides):
    historical = with_controls(_GATE.fixture_record())
    derivative = with_controls(_GATE.fixture_record(), grain="coarse")
    base = {
        "evidenceId": "p137-tc03",
        "repeat": "save",
        "historical": historical,
        "derivative": derivative,
        "operation": "save",
        "changed": ["grain"],
        "historicalVersion": "catalogue-1",
        "derivativeVersion": "catalogue-2",
    }
    base.update(overrides)
    return base


class TCP13703(unittest.TestCase):
    def assert_contract(self, result, evidence="p137-tc03"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P137-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 capture was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_grain_edit_versions_the_reconstruction(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        detail = result["preservedResults"][1]
        self.assertEqual(detail["derivativeVersion"], "catalogue-2")
        self.assertEqual(detail["changed"], ["grain"])
        stock = next(field for field in detail["historicalFacts"] if field["name"] == "stock")
        self.assertEqual(stock["value"], "Eastman 5293")
        self.assertEqual(stock["state"], "fact")
        grain = next(field for field in detail["retainedFields"] if field["name"] == "grain")
        self.assertEqual(grain["state"], "reconstruction")
        self.assertEqual(grain["value"], "coarse")
        lens = next(field for field in detail["retainedFields"] if field["name"] == "lens")
        self.assertEqual(lens["state"], "unknown")
        self.assertEqual(tuple(detail["stateCounts"]), _GATE.STATES)
        self.assertEqual(_MODULE.CASE["name"], "Creative edit overwrites evidence")

    def test_operations_do_not_rewrite_facts(self):
        for operation in ("save", "rename", "share", "update"):
            result = evaluate(payload(operation=operation, repeat=operation))
            self.assert_contract(result)
            self.assertEqual(result["decision"], "recorded", operation)

    def test_user_preference_cannot_replace_sourced_stock(self):
        derivative = with_controls(_GATE.fixture_record(), grain="coarse")
        for field in derivative["fields"]:
            if field["name"] == "stock":
                field["value"] = "user-favorite-stock"
        result = evaluate(payload(derivative=derivative))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.USER_PREFERENCE, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        stock = next(field for field in result["preservedResults"][1]["historicalFacts"] if field["name"] == "stock")
        self.assertEqual(stock["value"], "Eastman 5293")
        self.assertEqual(stock["source_id"], "src-northwater-stock")

    def test_reconstruction_relabel_is_rejected(self):
        derivative = with_controls(_GATE.fixture_record(), grain="coarse")
        for field in derivative["fields"]:
            if field["name"] == "virtual_lens":
                field.update({
                    "state": "fact",
                    "source_id": "src-user",
                    "priorState": "reconstruction",
                })
        result = evaluate(payload(derivative=derivative, repeat="update"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.RELABELLED_FACT, result["rejectedClaims"])
        virtual = next(field for field in result["preservedResults"][1]["retainedFields"] if field["name"] == "virtual_lens")
        self.assertEqual(virtual["state"], "reconstruction")

    def test_same_version_is_rejected(self):
        result = evaluate(payload(derivativeVersion="catalogue-1"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.VERSION_NOT_CREATED, result["rejectedClaims"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(operation="overwrite"))
