"""Tests for TC-P139-03."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p139_tc03",
    Path(__file__).resolve().parents[1] / "gates" / "p139_tc03.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p139-tc03",
        "repeat": "save",
        "operation": "save",
    }
    base.update(_MODULE._CORE.bundle_for())
    base.update(overrides)
    return base


class TCP13903(unittest.TestCase):
    def assert_contract(self, result, evidence="p139-tc03"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P139-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(any(isinstance(item, str) and item.startswith("fact_hash=") for item in result["preservedResults"]))
        self.assertTrue(result["reasons"])

    def test_aperture_and_contrast_edit_keeps_the_fact_hash(self):
        body = payload()
        before = _MODULE._CORE.canonical_json(body["productionFacts"])
        result = evaluate(body)
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(_MODULE._CORE.canonical_json(body["productionFacts"]), before)
        self.assertIn("rr-2 changed=virtualAperture,printContrast", result["reasons"])
        self.assertIn("fact hash unchanged", result["reasons"])
        self.assertEqual(body["reconstructions"][0]["fact_hash"], body["reconstructions"][1]["fact_hash"])
        self.assertNotEqual(
            body["reconstructions"][0]["parameter_hash"],
            body["reconstructions"][1]["parameter_hash"],
        )

    def test_parameters_that_copy_documented_settings_are_rejected(self):
        body = payload(operation="update", repeat="update")
        child = body["reconstructions"][1]
        child["parameters"] = dict(child["parameters"])
        child["parameters"]["documentedAperture"] = "T8"
        child["parameter_hash"] = _MODULE._CORE.compute_parameter_hash(
            child["parent_id"],
            child["fact_hash"],
            child["parameters"],
        )
        result = evaluate(body)
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE._CORE.DOCUMENTED_KEY_OVERWRITTEN, result["rejectedClaims"])
        self.assertEqual(body["reconstructions"][0]["fact_hash"], body["fact_hash"])
        self.assertIn("p139-tc03", result["preservedResults"])

    def test_rename_share_and_mutated_facts(self):
        renamed = evaluate(payload(operation="rename", repeat="rename"))
        self.assertEqual(renamed["decision"], "recorded")
        shared = evaluate(payload(operation="share", repeat="share", evidenceId="p139-tc03-share"))
        self.assert_contract(shared, "p139-tc03-share")
        self.assertEqual(shared["decision"], "recorded")
        mutated = evaluate(payload(mutated_facts=True))
        self.assertEqual(mutated["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, mutated["rejectedClaims"])
        self.assertIn(_MODULE._CORE.MUTATED_FACTS, mutated["rejectedClaims"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(operation="delete"))
