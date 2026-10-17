"""Tests for TC-P142-05."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p142_tc05",
    Path(__file__).resolve().parents[1] / "gates" / "p142_tc05.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p142-tc05",
        "repeat": "still",
        "source": _GATE.fixture_source(),
        "reference": _GATE.fixture_reference(),
        "suggestion": _GATE.fixture_suggestion(),
        "asset": _MODULE.clean_asset(),
    }
    base.update(overrides)
    return base


class TCP14205(unittest.TestCase):
    def assert_contract(self, result, evidence="p142-tc05"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P142-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertFalse(result["preservedResults"][1]["newSource"])

    def test_citation_is_kept_and_bytes_stay_out_of_the_bundle(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        asset = result["preservedResults"][2]
        self.assertFalse(asset["bundled"])
        self.assertEqual(asset["redistribution"], "unknown")
        self.assertIn("redistribution unknown", asset["citation"])

    def test_public_visibility_is_not_a_licence(self):
        result = evaluate(payload(asset=_MODULE.clean_asset(treatedAsLicence=True)))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_unapproved_bytes_are_rejected(self):
        result = evaluate(payload(asset=_MODULE.clean_asset(bundled=True), repeat="commercial-lut"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.BUNDLED, result["rejectedClaims"])

    def test_granted_redistribution_may_bundle(self):
        asset = _MODULE.clean_asset(redistribution="granted", bundled=True, kind="profile")
        result = evaluate(payload(asset=asset, repeat="profile"))
        self.assertEqual(result["decision"], "recorded")
        self.assertTrue(result["preservedResults"][2]["bundled"])

    def test_repeat_kinds_preserve_a_different_evidence_id(self):
        for kind, evidence in (
            ("promotional-image", "p142-tc05-promo"),
            ("commercial-lut", "p142-tc05-lut"),
            ("research-weights", "p142-tc05-weights"),
        ):
            result = evaluate(payload(
                evidenceId=evidence,
                repeat=kind,
                asset=_MODULE.clean_asset(kind=kind),
            ))
            self.assert_contract(result, evidence)
            self.assertEqual(result["decision"], "recorded")
            self.assertEqual(result["preservedResults"][2]["kind"], kind)

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(asset=_MODULE.clean_asset(kind="footage")))
