"""Tests for TC-P125-08."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p125_tc08",
    Path(__file__).resolve().parents[1] / "gates" / "p125_tc08.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
PRIVATE = "/home/ada/private/raw/clip.dng"


def payload(**overrides):
    base = {
        "evidenceId": "p125-bundle",
        "repeat": "clean-log",
        "presentation": "clean-log",
        "privatePaths": [PRIVATE],
        "pathsRedacted": True,
        "signalInterpretationPresent": True,
        "recipeMetadataPresent": True,
        "presentedAsSelfDescribing": False,
    }
    base.update(overrides)
    return base


class TCP12508(unittest.TestCase):
    def assert_contract(self, result, evidence="p125-bundle"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P125-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))
        self.assertNotIn(PRIVATE, json.dumps(result))

    def test_constants(self):
        self.assertEqual(_MODULE.NAME, "Shared bundle privacy and interpretation")
        self.assertEqual(
            _MODULE.EXPECTED,
            "Redact personal information while retaining the technical interpretation needed for correct use.",
        )
        self.assertEqual(
            _MODULE.NEGATIVE,
            "A Log master without its required interpretation record must not be silently presented as universally self-describing.",
        )
        self.assertEqual(
            _MODULE.REPEAT,
            "Repeat clean Log, rendered SDR, HDR-derived looks, and unverified partial exports.",
        )

    def test_redacted_log_with_interpretation_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        kept = result["preservedResults"][1]
        self.assertEqual(kept["privatePathCount"], 1)
        self.assertTrue(kept["pathsRedacted"])
        self.assertTrue(kept["signalInterpretationPresent"])
        self.assertTrue(kept["recipeMetadataPresent"])

    def test_log_master_without_interpretation_is_rejected(self):
        result = evaluate(payload(signalInterpretationPresent=False, presentedAsSelfDescribing=True, pathsRedacted=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.LOG_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.SIGNAL_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.PATH_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_rendered_sdr_can_omit_a_log_interpretation(self):
        result = evaluate(
            payload(
                evidenceId="p125-sdr",
                repeat="rendered-sdr",
                presentation="rendered-sdr",
                privatePaths=[],
                pathsRedacted=False,
                signalInterpretationPresent=False,
                presentedAsSelfDescribing=False,
            )
        )
        self.assert_contract(result, "p125-sdr")
        self.assertEqual(result["decision"], "recorded")

    def test_unverified_partial_is_not_self_describing(self):
        result = evaluate(
            payload(
                evidenceId="p125-partial",
                repeat="unverified-partial",
                presentation="unverified-partial",
                privatePaths=[],
                signalInterpretationPresent=False,
                presentedAsSelfDescribing=True,
            )
        )
        self.assert_contract(result, "p125-partial")
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.PARTIAL_TOKEN, result["rejectedClaims"])

    def test_hdr_without_signal_is_rejected(self):
        result = evaluate(
            payload(
                repeat="hdr-derived",
                presentation="hdr-derived",
                signalInterpretationPresent=False,
                privatePaths=[],
            )
        )
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.SIGNAL_TOKEN, result["rejectedClaims"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(recipeMetadataPresent="yes"))
