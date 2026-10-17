"""Tests for TC-P143-03."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p143_tc03",
    Path(__file__).resolve().parents[1] / "gates" / "p143_tc03.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p143-tc03",
        "repeat": "recipe-save",
        "looks": _GATE.fixture_looks(),
        "dropAmbiguous": False,
        "historicalFacts": {"camera": "Panaflex", "lens": "Cooke S4", "stock": "5219"},
        "derivativeEdits": {"grade": 0.25, "grain": 0.1},
        "newVersionId": "recon-2",
        "overwritesHistoricalFacts": False,
        "preferenceReplacesMetadata": False,
    }
    base.update(overrides)
    return base


class TCP14303(unittest.TestCase):
    def assert_contract(self, result, evidence="p143-tc03"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P143-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 capture was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_new_version_keeps_historical_facts_and_distinct_releases(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        record = result["preservedResults"][2]
        self.assertEqual(record["historicalFacts"]["stock"], "5219")
        self.assertEqual(record["newVersionId"], "recon-2")
        self.assertEqual(record["derivativeEdits"]["grade"], 0.25)
        self.assertEqual(
            result["preservedResults"][1]["distinctReleaseIds"]["reference-film"],
            ["digital-sdr", "theatrical-35mm"],
        )

    def test_preference_replacing_metadata_is_rejected(self):
        result = evaluate(payload(preferenceReplacesMetadata=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertEqual(result["preservedResults"][2]["historicalFacts"]["camera"], "Panaflex")

    def test_edit_without_a_new_version_is_rejected(self):
        result = evaluate(payload(newVersionId=None))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.MISSING_VERSION, result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][2]["historicalFacts"]["lens"], "Cooke S4")

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p143-tc03-share"
        result = evaluate(payload(evidenceId=evidence, repeat="share"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(derivativeEdits={"exposure": 1}))
