"""Tests for TC-P101-06."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p101_tc06",
    Path(__file__).resolve().parents[1] / "gates" / "p101_tc06.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p101-tc06",
        "repeat": "rapid camera movement",
        "sourceTimestampNs": 1000000,
        "sourceCrop": [0, 0, 4, 2],
        "values": [0.25, 0.5, 0.75],
        "identity": {"timestampNs": 1000000, "crop": [0, 0, 4, 2]},
        "reprojected": False,
    }
    base.update(overrides)
    return base


class TCP10106(unittest.TestCase):
    def assert_contract(self, result, evidence="p101-tc06"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P101-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(any("physical S23 measurement was not run" in item for item in result["openQuestions"]))

    def test_matching_timestamp_and_crop_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("depth timestamp and crop match the source", " ".join(result["reasons"]))

    def test_bare_float_list_is_rejected(self):
        result = evaluate(payload(identity=None))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("float-array-without-temporal-geometric-identity", result["rejectedClaims"])

    def test_timestamp_or_crop_mismatch_is_rejected(self):
        late = evaluate(payload(identity={"timestampNs": 1000033, "crop": [0, 0, 4, 2]}))
        cropped = evaluate(payload(identity={"timestampNs": 1000000, "crop": [1, 0, 3, 2]}))
        claimed = evaluate(payload(
            identity={"timestampNs": 1000033, "crop": [0, 0, 4, 2]},
            reprojected=True,
        ))
        for result in (late, cropped, claimed):
            self.assert_contract(result)
            self.assertEqual(result["decision"], "rejected")
            self.assertIn("stale-depth-timestamp-or-crop-mismatch", result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p101-tc06-scene-cut"
        result = evaluate(payload(evidenceId=evidence, repeat="scene cuts"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(values=[]))
        with self.assertRaises(ValueError):
            evaluate(payload(identity={"timestampNs": 1}))
