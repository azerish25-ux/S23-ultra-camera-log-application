"""Tests for TC-P121-08."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p121_tc08",
    Path(__file__).resolve().parents[1] / "gates" / "p121_tc08.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p121-bundle",
        "repeat": "clean-log",
        "paths": ["/sdcard/DCIM/private-clip.mov", "file://export/look"],
        "masterKind": "log",
        "interpretationRecord": {"transfer": "logc3", "range": "full"},
        "recipeMetadataPresent": True,
        "signalMetadataPresent": True,
        "presentedAsSelfDescribing": False,
        "verified": True,
    }
    base.update(overrides)
    return base


class TCP12108(unittest.TestCase):
    def assert_contract(self, result, evidence="p121-bundle"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P121-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))

    def test_constants(self):
        self.assertEqual(_MODULE.NAME, "Shared bundle privacy and interpretation")
        self.assertEqual(
            _MODULE.INTERVENTION,
            "Export a result with private paths or without necessary signal and recipe metadata.",
        )
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

    def test_clean_log_redacts_paths_and_keeps_interpretation(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        kept = result["preservedResults"][1]
        self.assertEqual(kept["redactedPaths"][0], "redacted://media")
        self.assertEqual(kept["redactedPaths"][1], "file://export/look")
        self.assertEqual(kept["interpretationRecord"]["transfer"], "logc3")
        self.assertFalse(kept["presentedAsSelfDescribing"])
        self.assertNotIn("/sdcard/", json.dumps(result["preservedResults"]))

    def test_log_without_interpretation_is_not_self_describing(self):
        result = evaluate(payload(interpretationRecord=None, presentedAsSelfDescribing=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.LOG_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.SELF_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIsNone(result["preservedResults"][1]["interpretationRecord"])
        self.assertNotIn("/sdcard/", json.dumps(result["preservedResults"]))

    def test_sdr_hdr_and_unverified_partial(self):
        sdr = evaluate(
            payload(
                evidenceId="p121-sdr",
                repeat="rendered-sdr",
                masterKind="sdr",
                paths=["file://export/sdr.mov"],
                interpretationRecord=None,
                presentedAsSelfDescribing=True,
            )
        )
        self.assert_contract(sdr, "p121-sdr")
        self.assertEqual(sdr["decision"], "recorded")
        self.assertEqual(sdr["preservedResults"][1]["redactedPaths"], ["file://export/sdr.mov"])
        hdr = evaluate(
            payload(
                repeat="hdr-derived",
                masterKind="hdr",
                interpretationRecord=None,
                presentedAsSelfDescribing=False,
            )
        )
        self.assertEqual(hdr["decision"], "rejected")
        self.assertIn("hdr-derived-without-interpretation", hdr["rejectedClaims"])
        partial = evaluate(
            payload(
                evidenceId="p121-partial",
                repeat="unverified-partial",
                masterKind="partial",
                interpretationRecord=None,
                recipeMetadataPresent=False,
                signalMetadataPresent=False,
                presentedAsSelfDescribing=False,
                verified=False,
            )
        )
        self.assert_contract(partial, "p121-partial")
        self.assertEqual(partial["decision"], "recorded")
        self.assertFalse(partial["preservedResults"][1]["verified"])
        claimed = evaluate(
            payload(
                repeat="unverified-partial",
                masterKind="partial",
                interpretationRecord=None,
                recipeMetadataPresent=False,
                signalMetadataPresent=False,
                presentedAsSelfDescribing=True,
                verified=True,
            )
        )
        self.assertEqual(claimed["decision"], "rejected")
        self.assertIn("unverified-partial-presented-as-complete", claimed["rejectedClaims"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(masterKind="sdr"))
        with self.assertRaises(ValueError):
            evaluate(payload(paths=[]))
