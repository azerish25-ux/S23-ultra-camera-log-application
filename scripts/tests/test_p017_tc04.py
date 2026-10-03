"""TC-P017-04 preview consumer stalls."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p017_tc04", Path(__file__).resolve().parents[1] / "gates" / "p017_tc04.py"
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
_TIMING = "gen2:30000us"


def payload(**overrides):
    base = {
        "consumer": "scopes",
        "sourceHealthy": True,
        "blocksSourceCapture": False,
        "sourceTiming": _TIMING,
        "resourceCount": 2,
        "resourceBound": 4,
    }
    base.update(overrides)
    return base


class TcP01704(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P017-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_constants_encode_the_case(self):
        self.assertIn("source acquisition", _MODULE.INTERVENTION)
        self.assertIn("source timing", _MODULE.EXPECTED)
        self.assertIn("cosmetic consumer", _MODULE.NEGATIVE)
        self.assertIn("depth_inference", _MODULE.CONSUMERS)
        self.assertIn("detached_display_surface", _MODULE.CONSUMERS)

    def test_scopes_drop_monitoring_and_keep_timing(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "monitoring_dropped")
        self.assertEqual(result["preservedResults"], [_TIMING])
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(any("scopes" in item for item in result["reasons"]))
        self.assertTrue(any("source timing unchanged" in item for item in result["reasons"]))

    def test_depth_inference_above_bound_reduces_instead_of_exhausting(self):
        result = evaluate(
            payload(consumer="depth_inference", resourceCount=8, resourceBound=4)
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "monitoring_dropped")
        self.assertEqual(result["preservedResults"], [_TIMING])
        self.assertTrue(any("exhausting" in item for item in result["reasons"]))
        self.assertTrue(any("depth_inference" in item for item in result["reasons"]))

    def test_thumbnail_generation_keeps_source_timing(self):
        timing = "gen2:33333us"
        result = evaluate(payload(consumer="thumbnail_generation", sourceTiming=timing))
        self.assertEqual(result["decision"], "monitoring_dropped")
        self.assertEqual(result["preservedResults"], [timing])

    def test_detached_display_does_not_block_source(self):
        result = evaluate(payload(consumer="detached_display_surface"))
        self.assertEqual(result["decision"], "monitoring_dropped")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_TIMING, result["preservedResults"])

    def test_cosmetic_consumer_blocking_source_is_rejected(self):
        result = evaluate(payload(consumer="scopes", blocksSourceCapture=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], ["cosmetic-blocks-source"])
        self.assertEqual(result["preservedResults"], [_TIMING])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_unhealthy_source_is_withheld_without_erasing_timing(self):
        result = evaluate(payload(sourceHealthy=False, consumer="film_preview" if False else "scopes"))
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["preservedResults"], [_TIMING])
        self.assertEqual(result["openQuestions"], ["source acquisition is not healthy"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "consumer": "histogram"},
            {**valid, "sourceHealthy": 1},
            {**valid, "sourceTiming": ""},
            {**valid, "resourceCount": -1},
            {**valid, "resourceBound": True},
            {**valid, "resourceCount": 1.5},
            {k: v for k, v in valid.items() if k != "consumer"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
