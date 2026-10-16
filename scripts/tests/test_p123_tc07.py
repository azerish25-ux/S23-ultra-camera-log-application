"""Tests for TC-P123-07."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p123_tc07",
    Path(__file__).resolve().parents[1] / "gates" / "p123_tc07.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p123-boundary",
        "chunks": [{"start": 0, "end": 2}, {"start": 2, "end": 4}],
        "assembledFrames": [0, 1, 2, 3, 4],
        "declaredContinuity": True,
        "rate": 23.976,
        "audioBearing": False,
        "sceneCutAtBoundary": False,
        "repeat": "fractional-rate",
    }
    base.update(overrides)
    return base


class TCP12307(unittest.TestCase):
    def assert_contract(self, result, evidence="p123-boundary"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P123-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))

    def test_constants(self):
        self.assertEqual(_MODULE.NAME, "Resume boundary duplication")
        self.assertEqual(
            _MODULE.NEGATIVE,
            "A playable movie with duplicated overlap frames must fail cadence integrity.",
        )
        self.assertIn("scene cuts", _MODULE.REPEAT)

    def test_overlap_is_emitted_once(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][1], [0, 1, 2, 3, 4])
        self.assertEqual(result["preservedResults"][2], [0, 1, 2, 3, 4])
        self.assertEqual(_MODULE.chunk_union([{"start": 0, "end": 2}, {"start": 2, "end": 4}]), [0, 1, 2, 3, 4])

    def test_duplicated_overlap_fails_cadence_integrity(self):
        result = evaluate(payload(assembledFrames=[0, 1, 2, 2, 3, 4], repeat="audio-bearing", audioBearing=True, rate=24))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("duplicated-overlap-frames", result["rejectedClaims"])
        self.assertIn("cadence-integrity", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertEqual(result["preservedResults"][1], [0, 1, 2, 3, 4])
        self.assertEqual(result["preservedResults"][2], [0, 1, 2, 2, 3, 4])

    def test_omitted_boundary_frame_is_rejected(self):
        result = evaluate(
            payload(
                assembledFrames=[0, 1, 3, 4],
                sceneCutAtBoundary=True,
                repeat="scene-cut",
                rate=24,
                evidenceId="p123-omit",
            )
        )
        self.assert_contract(result, "p123-omit")
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("omitted-boundary-frame", result["rejectedClaims"])
        self.assertTrue(result["preservedResults"][3]["sceneCutAtBoundary"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(chunks=[{"start": 0, "end": 1}, {"start": 3, "end": 4}]))
        with self.assertRaises(ValueError):
            evaluate(payload(rate=24))
