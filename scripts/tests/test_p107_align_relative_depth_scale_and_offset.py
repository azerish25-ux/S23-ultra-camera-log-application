"""Host checks for P107. Not a physical S23 probe."""

from __future__ import annotations

import importlib.util
import json
import math
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p107_align_relative_depth_scale_and_offset",
    Path(__file__).resolve().parents[1] / "gates" / "p107_align_relative_depth_scale_and_offset.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
assess = _MODULE.assess
evaluate = _MODULE.evaluate
fit_relative_depth = _MODULE.fit_relative_depth
MUTANT = _MODULE.MUTANT
ORACLE = _MODULE.ORACLE
BASE_REVISION = _MODULE.BASE_REVISION

_KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
_ROOT = Path(__file__).resolve().parents[2]


def _token(result, prefix):
    for item in result["preservedResults"]:
        if isinstance(item, str) and item.startswith(prefix):
            return float(item.split(":", 1)[1])
    raise AssertionError(prefix)


def document(**overrides):
    value = {
        "schemaVersion": 1,
        "phase": "P107",
        "implementationBaseRevision": BASE_REVISION,
        "evidenceId": "p107-background-alignment",
        "claim": "stationary-background-scale-and-offset",
        "applyMutant": False,
        "aligned_unit": "relative",
        "reference_unit": "relative",
        "force_unit_scale": False,
        "holdout_in_fit": False,
        "pairs": [
            {"id": "bg-a", "depth_rel": 0.1, "depth_ref": 0.7},
            {"id": "bg-b", "depth_rel": 0.3, "depth_ref": 1.1},
            {"id": "bg-c", "depth_rel": 0.5, "depth_ref": 1.5},
        ],
        "holdout": [
            {"id": "bg-d", "depth_rel": 0.4, "depth_ref": 1.3},
        ],
        "foreground": [
            {"id": "near-object", "depth_rel": 0.05, "depth_ref": 0.3},
        ],
    }
    value.update(overrides)
    return value


class P107Tests(unittest.TestCase):
    def assert_contract(self, result, evidence="p107-background-alignment"):
        self.assertEqual(tuple(result), _KEYS)
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(result["decision"], {"recorded", "rejected"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23" in item and "not run" in item for item in result["openQuestions"]))

    def test_constants_match_the_spec(self):
        self.assertEqual(BASE_REVISION, "3fbad4bc0e0336e273d2723ec873f001e8865323")
        self.assertEqual(_MODULE.PHASE, "P107")
        self.assertEqual(_MODULE.GOAL, "Prevent arbitrary model normalization from becoming visible focus breathing.")
        self.assertEqual(_MODULE.MUTANT, "Renormalize each depth map using its current minimum and maximum.")
        self.assertEqual(_MODULE.DELIVERABLE, "Relative-depth alignment and focus-pumping tests")
        self.assertEqual(_MODULE.MIN_PAIRS, 3)

    def test_fixture_json_is_recorded_not_qualified(self):
        payload = json.loads((_ROOT / "docs" / "P107_ALIGN_RELATIVE_DEPTH_SCALE_AND_OFFSET.json").read_text())
        result = assess(payload)
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["caseId"], "P107")
        self.assertAlmostEqual(_token(result, "scale:"), 2.0, places=9)
        self.assertAlmostEqual(_token(result, "offset:"), 0.5, places=9)
        self.assertAlmostEqual(_token(result, "rmse:"), 0.0, places=9)
        self.assertAlmostEqual(_token(result, "holdout-rmse:"), 0.0, places=9)
        self.assertIn(ORACLE, " ".join(result["reasons"]))
        self.assertTrue(any("normal equations" in item for item in result["reasons"]))

    def test_analytic_normal_equations(self):
        fit = fit_relative_depth([(0.0, 0.0), (1.0, 1.0), (2.0, 3.0)])
        self.assertAlmostEqual(fit["scale"], 1.5, places=9)
        self.assertAlmostEqual(fit["offset"], -1.0 / 6.0, places=9)
        self.assertAlmostEqual(fit["rmse"], math.sqrt(1.0 / 18.0), places=9)

    def test_mutant_is_rejected_and_evidence_remains(self):
        result = assess(document(applyMutant=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(MUTANT, result["rejectedClaims"])

    def test_negative_scale_is_depth_reversed(self):
        result = evaluate(
            {
                "evidenceId": "p107-reversed",
                "claim": "reversed",
                "pairs": [(0.0, 3.0), (1.0, 2.0), (2.0, 1.0)],
            }
        )
        self.assert_contract(result, "p107-reversed")
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("negative-scale", result["rejectedClaims"])
        self.assertIn("depth-reversed", result["rejectedClaims"])
        self.assertAlmostEqual(_token(result, "scale:"), -1.0, places=9)

    def test_fewer_than_three_points_is_rejected(self):
        result = evaluate({"evidenceId": "p107-short", "pairs": [(0.0, 1.0), (1.0, 2.0)]})
        self.assert_contract(result, "p107-short")
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("fewer-than-3-points", result["rejectedClaims"])

    def test_non_finite_depth_is_rejected(self):
        result = evaluate(
            {
                "evidenceId": "p107-nan",
                "pairs": [(0.0, 0.0), (1.0, float("nan")), (2.0, 2.0)],
            }
        )
        self.assert_contract(result, "p107-nan")
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("non-finite-depth", result["rejectedClaims"])
        self.assertNotIn("scale:nan", result["preservedResults"])

    def test_metric_metres_on_relative_reference_is_rejected(self):
        result = assess(document(aligned_unit="metric metres", reference_unit="relative"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("metric-metres-on-relative-reference", result["rejectedClaims"])

    def test_constant_bias_fix_is_rejected_when_scale_is_far_from_one(self):
        result = assess(document(force_unit_scale=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("constant-bias-fix", result["rejectedClaims"])

    def test_unit_scale_is_recorded_when_it_is_the_true_scale(self):
        result = evaluate(
            {
                "evidenceId": "p107-unit",
                "claim": "unit",
                "force_unit_scale": True,
                "pairs": [(0.0, 1.0), (1.0, 2.0), (2.0, 3.0)],
            }
        )
        self.assert_contract(result, "p107-unit")
        self.assertEqual(result["decision"], "recorded")
        self.assertAlmostEqual(_token(result, "scale:"), 1.0, places=9)
        self.assertAlmostEqual(_token(result, "offset:"), 1.0, places=9)
        self.assertEqual(result["rejectedClaims"], [])

    def test_holdout_does_not_enter_the_fit(self):
        first = evaluate(
            {
                "evidenceId": "p107-hold",
                "pairs": [
                    {"id": "a", "depth_rel": 0.0, "depth_ref": 0.0},
                    {"id": "b", "depth_rel": 1.0, "depth_ref": 1.0},
                    {"id": "c", "depth_rel": 2.0, "depth_ref": 3.0},
                ],
                "holdout": [{"id": "h", "depth_rel": 4.0, "depth_ref": 0.0}],
            }
        )
        second = evaluate(
            {
                "evidenceId": "p107-hold",
                "pairs": [
                    {"id": "a", "depth_rel": 0.0, "depth_ref": 0.0},
                    {"id": "b", "depth_rel": 1.0, "depth_ref": 1.0},
                    {"id": "c", "depth_rel": 2.0, "depth_ref": 3.0},
                ],
                "holdout": [{"id": "h", "depth_rel": 4.0, "depth_ref": 100.0}],
            }
        )
        self.assertEqual(first["decision"], "recorded")
        self.assertAlmostEqual(_token(first, "scale:"), _token(second, "scale:"), places=12)
        self.assertAlmostEqual(_token(first, "offset:"), _token(second, "offset:"), places=12)
        self.assertGreater(_token(second, "holdout-rmse:"), _token(first, "holdout-rmse:"))

    def test_holdout_flag_and_id_overlap_are_rejected(self):
        flagged = evaluate(
            {
                "evidenceId": "p107-leak-flag",
                "pairs": [
                    {"id": "a", "depth_rel": 0.0, "depth_ref": 0.0},
                    {"id": "b", "depth_rel": 1.0, "depth_ref": 1.0},
                    {"id": "c", "depth_rel": 2.0, "depth_ref": 2.0},
                ],
                "holdout": [{"id": "h", "depth_rel": 3.0, "depth_ref": 3.0}],
                "holdout_in_fit": True,
            }
        )
        overlap = evaluate(
            {
                "evidenceId": "p107-leak-id",
                "pairs": [
                    {"id": "a", "depth_rel": 0.0, "depth_ref": 0.0},
                    {"id": "b", "depth_rel": 1.0, "depth_ref": 1.0},
                    {"id": "h", "depth_rel": 3.0, "depth_ref": 9.0},
                ],
                "holdout": [{"id": "h", "depth_rel": 3.0, "depth_ref": 3.0}],
            }
        )
        self.assertEqual(flagged["decision"], "rejected")
        self.assertIn("holdout-leakage", flagged["rejectedClaims"])
        self.assertEqual(overlap["decision"], "rejected")
        self.assertIn("holdout-leakage", overlap["rejectedClaims"])
        self.assertNotIn("holdout-rmse:0", overlap["preservedResults"])

    def test_ill_conditioned_constant_relative_depth_is_rejected(self):
        result = evaluate(
            {
                "evidenceId": "p107-singular",
                "pairs": [(1.0, 1.0), (1.0, 2.0), (1.0, 3.0)],
            }
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("ill-conditioned", result["rejectedClaims"])

    def test_foreground_is_excluded_from_the_fit(self):
        alone = fit_relative_depth([(0.1, 0.7), (0.3, 1.1), (0.5, 1.5)])
        contaminated = fit_relative_depth([(0.1, 0.7), (0.3, 1.1), (0.5, 1.5), (0.05, 0.3)])
        result = assess(document())
        self.assertAlmostEqual(_token(result, "scale:"), alone["scale"], places=9)
        self.assertNotAlmostEqual(contaminated["scale"], alone["scale"], places=6)

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            assess(document(schemaVersion=2))
        with self.assertRaises(ValueError):
            fit_relative_depth([(0.0, 0.0), (1.0, float("inf")), (2.0, 2.0)])
        with self.assertRaises(ValueError):
            evaluate({"evidenceId": "x", "pairs": "nope"})
