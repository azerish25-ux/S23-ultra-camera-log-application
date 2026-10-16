"""Tests for TC-P123-08."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p123_tc08",
    Path(__file__).resolve().parents[1] / "gates" / "p123_tc08.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p123-bundle",
        "kind": "clean-log",
        "privatePaths": ["/home/user/clip.mov"],
        "exportedPaths": ["[redacted]/clip.mov"],
        "interpretation": {"signal": "logc3", "recipe": "ei800"},
        "presentedAsSelfDescribing": False,
        "repeat": "clean-log",
    }
    base.update(overrides)
    return base


class TCP12308(unittest.TestCase):
    def assert_contract(self, result, evidence="p123-bundle"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P123-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))

    def test_constants(self):
        self.assertEqual(_MODULE.NAME, "Shared bundle privacy and interpretation")
        self.assertEqual(
            _MODULE.NEGATIVE,
            "A Log master without its required interpretation record must not be silently presented as universally self-describing.",
        )
        self.assertIn("unverified partial", _MODULE.REPEAT)

    def test_redacted_log_master_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][1]["interpretation"]["signal"], "logc3")
        self.assertEqual(result["preservedResults"][1]["interpretation"]["recipe"], "ei800")
        self.assertEqual(result["preservedResults"][2], ["/home/user/clip.mov"])
        self.assertNotIn("/home/user/clip.mov", result["preservedResults"][1]["exportedPaths"])

    def test_log_without_interpretation_is_rejected(self):
        result = evaluate(payload(interpretation=None, presentedAsSelfDescribing=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("log-master-without-interpretation-record", result["rejectedClaims"])
        self.assertIn("log-presented-as-universally-self-describing", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIsNone(result["preservedResults"][1]["interpretation"])

    def test_private_path_and_partial_export_are_rejected(self):
        leaked = evaluate(payload(exportedPaths=["/home/user/clip.mov"]))
        self.assert_contract(leaked)
        self.assertEqual(leaked["decision"], "rejected")
        self.assertIn("private-path-not-redacted", leaked["rejectedClaims"])
        partial = evaluate(
            payload(
                evidenceId="p123-partial",
                kind="unverified-partial",
                repeat="unverified-partial",
                interpretation={"recipe": "draft"},
                presentedAsSelfDescribing=True,
            )
        )
        self.assert_contract(partial, "p123-partial")
        self.assertEqual(partial["decision"], "rejected")
        self.assertIn("unverified-partial-presented-as-complete", partial["rejectedClaims"])

    def test_sdr_and_hdr_interpretation(self):
        sdr = evaluate(
            payload(
                evidenceId="p123-sdr",
                kind="rendered-sdr",
                repeat="rendered-sdr",
                interpretation={"recipe": "display"},
                privatePaths=[],
            )
        )
        self.assert_contract(sdr, "p123-sdr")
        self.assertEqual(sdr["decision"], "recorded")
        hdr = evaluate(
            payload(
                kind="hdr-derived",
                repeat="hdr-derived",
                interpretation={"signal": "hlg", "recipe": "look"},
            )
        )
        self.assert_contract(hdr)
        self.assertEqual(hdr["decision"], "rejected")
        self.assertIn("interpretation-record-incomplete", hdr["rejectedClaims"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(repeat="rendered-sdr"))
        with self.assertRaises(ValueError):
            evaluate(payload(interpretation={}))
