"""Host checks for P106. Not a physical S23 probe."""

from __future__ import annotations

import importlib.util
import json
import math
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p106_implement_flow_based_history_reprojection",
    Path(__file__).resolve().parents[1] / "gates" / "p106_implement_flow_based_history_reprojection.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
assess = _MODULE.assess
evaluate = _MODULE.evaluate
MUTANT = _MODULE.MUTANT
ORACLE = _MODULE.ORACLE
BASE_REVISION = _MODULE.BASE_REVISION
FORWARD_BACKWARD_INCONSISTENCY_PX = _MODULE.FORWARD_BACKWARD_INCONSISTENCY_PX

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def _point(x, y, depth, dx, dy, rdx=None, rdy=None):
    point = {"x": x, "y": y, "depth": depth, "dx": dx, "dy": dy}
    if rdx is None:
        rdx = -dx
        rdy = -dy
    point["rdx"] = rdx
    point["rdy"] = rdy
    return point


def document(**overrides):
    value = {
        "schemaVersion": 1,
        "phase": "P106",
        "implementationBaseRevision": BASE_REVISION,
        "evidenceId": "p106-translating-square",
        "claim": "synthetic-host-fixture",
        "frame_width": 8,
        "frame_height": 8,
        "motion_px": 2,
        "prev_timestamp": "t0",
        "curr_timestamp": "t1",
        "fill_unknowns_as_measured": False,
        "points": [
            _point(1, 2, 0.35, 2, 0),
            _point(2, 2, 0.35, 2, 0),
            _point(1, 3, 0.35, 2, 0),
            _point(2, 3, 0.35, 2, 0),
            _point(7, 2, 0.35, 2, 0),
        ],
    }
    value.update(overrides)
    return value


class P106Tests(unittest.TestCase):
    def assert_contract(self, result, evidence="p106-translating-square"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "P106")
        self.assertIn(result["decision"], {"recorded", "rejected"})
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(any("physical S23 measurement was not run" in item for item in result["openQuestions"]))
        record = result["preservedResults"][2]
        self.assertIn("prev_timestamp", record)
        self.assertIn("curr_timestamp", record)

    def test_translation_aligns_square_and_leaves_exit_unknown(self):
        result = assess(document())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn(ORACLE, " ".join(result["reasons"]))
        samples = result["preservedResults"][2]["samples"]
        self.assertEqual([(sample["x"], sample["y"], sample["depth"], sample["status"]) for sample in samples[:4]], [
            (3, 2, 0.35, "measured"),
            (4, 2, 0.35, "measured"),
            (3, 3, 0.35, "measured"),
            (4, 3, 0.35, "measured"),
        ])
        self.assertEqual(samples[4]["x"], 9)
        self.assertEqual(samples[4]["status"], "unknown")
        self.assertIsNone(samples[4]["depth"])
        self.assertEqual(samples[4]["cause"], "outside-frame")
        self.assertEqual(result["preservedResults"][2]["prev_timestamp"], "t0")
        self.assertEqual(result["preservedResults"][2]["curr_timestamp"], "t1")

    def test_rotation_keeps_source_depth_at_the_rotated_pixel(self):
        # 90 degree CCW about (4, 4): (3, 3) -> (5, 3), (5, 3) -> (5, 5).
        result = assess(document(
            frame_width=10,
            frame_height=10,
            points=[
                _point(3, 3, 0.55, 2, 0),
                _point(5, 3, 0.55, 0, 2),
            ],
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        samples = result["preservedResults"][2]["samples"]
        self.assertEqual(samples[0]["x"], 5)
        self.assertEqual(samples[0]["y"], 3)
        self.assertEqual(samples[0]["depth"], 0.55)
        self.assertEqual(samples[1]["x"], 5)
        self.assertEqual(samples[1]["y"], 5)
        self.assertEqual(samples[1]["status"], "measured")

    def test_zero_flow_with_motion_is_history_pasted_without_flow(self):
        result = assess(document(
            points=[_point(1, 2, 0.35, 0, 0), _point(2, 2, 0.35, 0, 0)],
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(MUTANT, result["rejectedClaims"])
        self.assertIn("history-pasted-without-flow", result["rejectedClaims"])
        self.assertIn("synthetic-host-fixture", result["preservedResults"])

    def test_stationary_zero_flow_is_recorded(self):
        result = assess(document(
            motion_px=0,
            points=[_point(2, 2, 0.4, 0, 0)],
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        sample = result["preservedResults"][2]["samples"][0]
        self.assertEqual(sample["x"], 2)
        self.assertEqual(sample["depth"], 0.4)
        self.assertEqual(sample["status"], "measured")

    def test_inconsistency_at_threshold_stays_measured_and_above_is_unknown(self):
        self.assertEqual(FORWARD_BACKWARD_INCONSISTENCY_PX, 1.0)
        on_threshold = assess(document(points=[_point(2, 2, 0.4, 1, 0, rdx=-1, rdy=1.0)]))
        self.assertEqual(on_threshold["decision"], "recorded")
        self.assertEqual(on_threshold["preservedResults"][2]["samples"][0]["status"], "measured")
        self.assertEqual(on_threshold["preservedResults"][2]["samples"][0]["depth"], 0.4)
        above = assess(document(points=[_point(2, 2, 0.4, 1, 0, rdx=-1, rdy=1.01)]))
        sample = above["preservedResults"][2]["samples"][0]
        self.assertEqual(sample["status"], "unknown")
        self.assertIsNone(sample["depth"])
        self.assertEqual(sample["cause"], "forward-backward-inconsistent")
        self.assertEqual(above["decision"], "recorded")
        self.assertTrue(math.hypot(1 + -1, 0 + 1.01) > 1.0)

    def test_filling_inconsistent_unknowns_from_neighbours_is_rejected(self):
        result = assess(document(
            fill_unknowns_as_measured=True,
            points=[
                _point(2, 2, 0.2, 1, 0),
                _point(3, 2, 0.8, 1, 0, rdx=-1, rdy=2),
            ],
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("unknowns-filled-from-neighbours-called-measured", result["rejectedClaims"])
        samples = result["preservedResults"][2]["samples"]
        self.assertEqual(samples[0]["depth"], 0.2)
        self.assertIsNone(samples[1]["depth"])
        self.assertNotEqual(samples[1]["depth"], samples[0]["depth"])

    def test_outside_sample_is_not_extrapolated_when_fill_is_requested(self):
        result = evaluate(document(
            fill_unknowns_as_measured=True,
            points=[_point(0, 1, 0.7, -1, 0), _point(2, 1, 0.3, 1, 0)],
        ))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("outside-frame-extrapolated-with-invented-depth", result["rejectedClaims"])
        outside = result["preservedResults"][2]["samples"][0]
        self.assertLess(outside["x"], 0)
        self.assertIsNone(outside["depth"])

    def test_missing_timestamps_are_rejected_and_evidence_remains(self):
        result = assess(document(prev_timestamp=None, curr_timestamp=""))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("missing-source-timestamps", result["rejectedClaims"])
        record = result["preservedResults"][2]
        self.assertIsNone(record["prev_timestamp"])
        self.assertIsNone(record["curr_timestamp"])

    def test_published_fixture_matches_the_reprojection_rule(self):
        path = Path(__file__).resolve().parents[2] / "docs" / "P106_IMPLEMENT_FLOW_BASED_HISTORY_REPROJECTION.json"
        result = assess(json.loads(path.read_text(encoding="utf-8")))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        samples = result["preservedResults"][2]["samples"]
        self.assertTrue(all(sample["status"] == "measured" and sample["depth"] == 0.35 for sample in samples[:4]))
        self.assertEqual(samples[4]["status"], "unknown")
        self.assertIsNone(samples[4]["depth"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            assess({})
        with self.assertRaises(ValueError):
            assess(document(implementationBaseRevision="not-the-spec"))
        with self.assertRaises(ValueError):
            assess(document(points=[_point(1, 1, float("nan"), 1, 0)]))
        with self.assertRaises(ValueError):
            assess(document(motion_px=-1))
        with self.assertRaises(ValueError):
            assess(document(frame_width=True))
        with self.assertRaises(ValueError):
            assess(document(points=[]))
        extra = document()
        extra["applyMutant"] = False
        with self.assertRaises(ValueError):
            assess(extra)
