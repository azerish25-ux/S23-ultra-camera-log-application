"""Tests for TC-P112-05."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p112_tc05",
    Path(__file__).resolve().parents[1] / "gates" / "p112_tc05.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p112-tc05",
        "repeat": "backlighting",
        "samples": [
            {"coverage": 1.0, "source": "partial"},
            {"coverage": 0.35, "source": "partial"},
            {"coverage": 0.0, "source": "partial"},
        ],
        "halo": 0.08,
        "halo_limit": 0.2,
    }
    base.update(overrides)
    return base


class TCP11205(unittest.TestCase):
    def assert_contract(self, result, evidence="p112-tc05"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P112-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])

    def test_partial_coverage_inside_halo_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])

    def test_dilated_binary_mask_is_rejected_and_evidence_remains(self):
        samples = [
            {"coverage": 0.0, "source": "dilated-binary"},
            {"coverage": 1.0, "source": "dilated-binary"},
            {"coverage": 1.0, "source": "dilated-binary"},
        ]
        result = evaluate(payload(samples=samples, halo=0.0))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("dilated-binary-person-mask", result["rejectedClaims"])

    def test_partial_coverage_with_excess_halo_is_rejected(self):
        result = evaluate(payload(halo=0.5, evidenceId="p112-tc05-halo", repeat="contrast"))
        self.assert_contract(result, "p112-tc05-halo")
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("temporal-halo-exceeds-safe-limit", result["rejectedClaims"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(samples=[{"coverage": 0.4, "source": "dilated-binary"}]))
