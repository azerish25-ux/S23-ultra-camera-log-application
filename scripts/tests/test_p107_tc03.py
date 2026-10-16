"""Tests for TC-P107-03."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p107_tc03",
    Path(__file__).resolve().parents[1] / "gates" / "p107_tc03.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p107-evidence",
        "repeat": "stationary-background",
        "claim": "background-alignment",
        "pairs": [
            {"id": "bg-a", "depth_rel": 0.1, "depth_ref": 0.7},
            {"id": "bg-b", "depth_rel": 0.3, "depth_ref": 1.1},
            {"id": "bg-c", "depth_rel": 0.5, "depth_ref": 1.5},
        ],
        "holdout": [{"id": "bg-d", "depth_rel": 0.4, "depth_ref": 1.3}],
        "aligned_unit": "relative",
        "reference_unit": "relative",
        "force_unit_scale": False,
        "holdout_in_fit": False,
        "applyMutant": False,
        "per_frame_minmax": False,
    }
    base.update(overrides)
    return base


def _token(result, prefix):
    for item in result["preservedResults"]:
        if isinstance(item, str) and item.startswith(prefix):
            return float(item.split(":", 1)[1])
    raise AssertionError(prefix)


class TCP10703(unittest.TestCase):
    def assert_contract(self, result, evidence="p107-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P107-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))

    def test_stable_background_alignment_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertAlmostEqual(_token(result, "scale:"), 2.0, places=9)
        self.assertAlmostEqual(_token(result, "offset:"), 0.5, places=9)
        self.assertAlmostEqual(_token(result, "rmse:"), 0.0, places=9)
        self.assertAlmostEqual(_token(result, "holdout-rmse:"), 0.0, places=9)
        self.assertTrue(any("normal equations" in item for item in result["reasons"]))

    def test_per_frame_minmax_is_rejected(self):
        result = evaluate(payload(per_frame_minmax=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("per-frame-minmax", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("p107-evidence", result["preservedResults"])

    def test_forced_unit_scale_and_metric_label_are_rejected(self):
        biased = evaluate(payload(force_unit_scale=True))
        self.assertEqual(biased["decision"], "rejected")
        self.assertIn("constant-bias-fix", biased["rejectedClaims"])
        labelled = evaluate(payload(aligned_unit="metric metres", reference_unit="relative"))
        self.assertEqual(labelled["decision"], "rejected")
        self.assertIn("metric-metres-on-relative-reference", labelled["rejectedClaims"])

    def test_holdout_leakage_is_rejected(self):
        result = evaluate(payload(holdout_in_fit=True, evidenceId="p107-leak"))
        self.assert_contract(result, "p107-leak")
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("holdout-leakage", result["rejectedClaims"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
