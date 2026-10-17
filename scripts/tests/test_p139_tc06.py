"""Tests for TC-P139-06."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p139_tc06",
    Path(__file__).resolve().parents[1] / "gates" / "p139_tc06.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
EDITIONS = [
    {"id": "theatrical", "release": "theatrical-35mm", "printContrast": 1},
    {"id": "digital", "release": "digital-dcp", "printContrast": 2},
    {"id": "hdr", "release": "hdr-master", "printContrast": 3},
    {"id": "unidentified", "release": "unidentified", "printContrast": None},
]


def payload(**overrides):
    base = {
        "evidenceId": "p139-tc06",
        "repeat": "theatrical",
        "editions": EDITIONS,
        "separateTargets": True,
        "uncertaintyExplicit": True,
    }
    base.update(_MODULE._CORE.bundle_for())
    base.update(overrides)
    return base


class TCP13906(unittest.TestCase):
    def assert_contract(self, result, evidence="p139-tc06"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P139-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(any(item.startswith("fact_hash=") for item in result["preservedResults"]))
        self.assertTrue(result["reasons"])

    def test_separate_editions_stay_unblended(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("edition=theatrical contrast=1", result["preservedResults"])
        self.assertIn("edition=hdr contrast=3", result["preservedResults"])
        self.assertIn("edition=unidentified contrast=None", result["preservedResults"])
        self.assertEqual(payload()["productionFacts"]["documentedPrintContrast"], "normal")

    def test_averaged_contrast_is_rejected(self):
        body = payload(separateTargets=False, uncertaintyExplicit=False, repeat="digital")
        child = body["reconstructions"][1]
        child["parameters"] = dict(child["parameters"])
        child["parameters"]["printContrast"] = 2
        child["parameter_hash"] = _MODULE._CORE.compute_parameter_hash(
            child["parent_id"],
            child["fact_hash"],
            child["parameters"],
        )
        result = evaluate(body)
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.INVENTED, result["rejectedClaims"])
        self.assertIn(_MODULE.UNIDENTIFIED, result["rejectedClaims"])
        self.assertEqual(body["productionFacts"]["documentedPrintContrast"], "normal")
        self.assertIn("p139-tc06", result["preservedResults"])

    def test_hdr_and_unidentified_repeats_preserve_evidence(self):
        hdr = evaluate(payload(repeat="hdr", evidenceId="p139-tc06-hdr"))
        self.assert_contract(hdr, "p139-tc06-hdr")
        self.assertEqual(hdr["decision"], "recorded")
        unknown = evaluate(payload(repeat="unidentified"))
        self.assertEqual(unknown["decision"], "recorded")

    def test_mutated_facts_are_rejected(self):
        result = evaluate(payload(mutated_facts=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE._CORE.MUTATED_FACTS, result["rejectedClaims"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(editions=EDITIONS[:1]))
