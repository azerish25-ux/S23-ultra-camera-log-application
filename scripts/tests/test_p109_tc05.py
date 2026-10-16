"""Tests for TC-P109-05."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p109_tc05",
    Path(__file__).resolve().parents[1] / "gates" / "p109_tc05.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def _sample(confidence, klass, matte, colour="mixed", called_opaque=False):
    return {
        "confidence": confidence,
        "class": klass,
        "matte": matte,
        "colour": colour,
        "called_opaque": called_opaque,
    }


def payload(**overrides):
    base = {
        "evidenceId": "p109-evidence",
        "repeat": "backlighting",
        "hair_threshold": 0.5,
        "band": 1,
        "minimum_unknown_coverage": 1.0,
        "inpaint_glass": False,
        "foreground_colour": "foreground",
        "samples": [
            _sample(0.99, "opaque", 1.0, "subject", True),
            _sample(0.99, "opaque", "unknown", "subject", False),
            _sample(0.2, "hair", 0.42, "mixed", False),
            _sample(0.9, "glass", "unknown", "mixed", False),
            _sample(0.99, "background", "unknown", "background", False),
            _sample(0.99, "background", 0.0, "background", False),
        ],
        "dilatedBinaryPersonMask": False,
    }
    base.update(overrides)
    return base


class TCP10905(unittest.TestCase):
    def assert_contract(self, result, evidence="p109-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P109-05")
        self.assertIn(result["decision"], {"recorded", "rejected"})
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))

    def test_partial_band_is_recorded_not_qualified(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("unknown-band 1,2,3,4", result["reasons"])

    def test_negative_dilated_mask_is_rejected_and_evidence_remains(self):
        result = evaluate(payload(dilatedBinaryPersonMask=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("dilated-binary-person-mask", result["rejectedClaims"])

    def test_mutant_hard_matte_is_rejected(self):
        result = evaluate(payload(
            repeat="crossing subjects",
            band=0,
            samples=[
                _sample(0.1, "hair", 0),
                _sample(0.1, "transparent", 1),
            ],
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("hard-matte-on-hair-or-transparent", result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p109-contrast"
        result = evaluate(payload(evidenceId=evidence, repeat="foreground-background contrast"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
