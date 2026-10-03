"""TC-P018-04 preview consumer stalls."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p018_tc04", Path(__file__).resolve().parents[1] / "gates" / "p018_tc04.py"
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
_TIMING = "pts:1000,1033,1066"


def payload(**overrides):
    base = {
        "consumer": "scopes",
        "sourceHealthy": True,
        "blocksSourceCapture": False,
        "sourceTiming": _TIMING,
        "monitoringBacklog": 4,
    }
    base.update(overrides)
    return base


class TcP01804(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P018-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_module_encodes_the_case_contract(self):
        self.assertIn("source acquisition remains healthy", _MODULE.INTERVENTION)
        self.assertIn("without corrupting source timing", _MODULE.EXPECTED)
        self.assertIn("blocks irreplaceable source capture", _MODULE.NEGATIVE)
        self.assertIn("scopes", _MODULE.REPEAT)
        self.assertIn("depth inference", _MODULE.REPEAT)

    def test_scopes_stall_drops_monitoring_and_keeps_timing(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "monitoring_reduced")
        self.assertEqual(result["preservedResults"], [_TIMING, "source-healthy"])
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(any("source timing unchanged" in item for item in result["reasons"]))

    def test_depth_inference_stall_keeps_the_same_timing(self):
        result = evaluate(payload(consumer="depth_inference", monitoringBacklog=2))
        self.assertContract(result)
        self.assertEqual(result["decision"], "monitoring_reduced")
        self.assertIn(_TIMING, result["preservedResults"])
        self.assertIn("source-healthy", result["preservedResults"])
        self.assertTrue(any("depth_inference" in item for item in result["reasons"]))

    def test_thumbnail_and_detached_surface_also_reduce(self):
        for consumer in ("thumbnail_generation", "detached_display_surface"):
            result = evaluate(payload(consumer=consumer, monitoringBacklog=1))
            with self.subTest(consumer=consumer):
                self.assertEqual(result["decision"], "monitoring_reduced")
                self.assertIn(_TIMING, result["preservedResults"])

    def test_cosmetic_consumer_blocking_source_is_rejected(self):
        result = evaluate(payload(consumer="thumbnail_generation", blocksSourceCapture=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], ["cosmetic-blocks-source", "thumbnail_generation"])
        self.assertIn(_TIMING, result["preservedResults"])
        self.assertNotIn("source-healthy", result["preservedResults"])

    def test_unhealthy_source_is_withheld_without_erasing_timing(self):
        result = evaluate(payload(sourceHealthy=False))
        self.assertEqual(result["decision"], "withheld")
        self.assertIn(_TIMING, result["preservedResults"])
        self.assertIn("source acquisition unhealthy", result["openQuestions"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "consumer": "lut"},
            {**valid, "sourceTiming": ""},
            {**valid, "monitoringBacklog": -1},
            {**valid, "monitoringBacklog": True},
            {**valid, "sourceHealthy": "true"},
            {k: v for k, v in valid.items() if k != "sourceTiming"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
