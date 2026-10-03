"""TC-P023-04 cosmetic preview consumers must not block the source."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "p023_tc04", Path(__file__).resolve().parents[1] / "gates" / "p023_tc04.py"
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def payload(**overrides):
    base = {
        "consumer": "scopes",
        "sourceHealthy": True,
        "consumerBlocksSource": False,
        "sourceTimingCorrupted": False,
        "resourcesExhausted": False,
        "staleMonitoringDropped": True,
        "sourceIdentity": "source-a",
        "framesKept": 12,
    }
    base.update(overrides)
    return base


class TcP02304(unittest.TestCase):
    def assert_contract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P023-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_module_encodes_case_text(self):
        self.assertIn("source acquisition remains healthy", _MODULE.INTERVENTION)
        self.assertIn("without corrupting source timing", _MODULE.EXPECTED)
        self.assertIn("blocks irreplaceable source capture", _MODULE.NEGATIVE)
        self.assertIn("depth_inference", _MODULE.CONSUMERS)
        self.assertIn("detached_display_surface", _MODULE.CONSUMERS)

    def test_scopes_drop_stale_monitoring(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "monitoring_reduced")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"], ["source-a", "frames:12"])
        self.assertTrue(any(_MODULE.EXPECTED in item for item in result["reasons"]))

    def test_depth_inference_does_not_exhaust_capture(self):
        result = evaluate(
            payload(consumer="depth_inference", sourceIdentity="source-depth", framesKept=3)
        )
        self.assert_contract(result)
        self.assertEqual(result["decision"], "monitoring_reduced")
        self.assertEqual(result["preservedResults"], ["source-depth", "frames:3"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_thumbnail_that_blocks_source_is_rejected(self):
        result = evaluate(
            payload(consumer="thumbnail_generation", consumerBlocksSource=True, framesKept=9)
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "monitoring_reduced"})
        self.assertIn("cosmetic-blocks-source", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"], ["source-a", "frames:9"])
        self.assertTrue(any(_MODULE.NEGATIVE in item for item in result["reasons"]))

    def test_detached_surface_that_corrupts_timing_is_rejected(self):
        result = evaluate(
            payload(
                consumer="detached_display_surface",
                sourceTimingCorrupted=True,
                sourceIdentity="source-display",
                framesKept=4,
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("source-timing-corrupted", result["rejectedClaims"])
        self.assertIn("source-display", result["preservedResults"])
        self.assertIn("frames:4", result["preservedResults"])

    def test_kept_stale_monitoring_is_rejected(self):
        result = evaluate(payload(consumer="focus_peaking" if False else "scopes", staleMonitoringDropped=False))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("stale-monitoring-kept", result["rejectedClaims"])
        self.assertIn("frames:12", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {**valid, "consumer": "lut"},
            {**valid, "sourceHealthy": False},
            {**valid, "framesKept": -1},
            {**valid, "framesKept": True},
            {**valid, "consumerBlocksSource": 1},
            {**valid, "sourceIdentity": "has space"},
            {**valid, "extra": True},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
