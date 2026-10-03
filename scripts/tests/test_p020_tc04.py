"""TC-P020-04 host checks. Not a physical S23 probe."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p020_tc04", Path(__file__).resolve().parents[1] / "gates" / "p020_tc04.py"
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
_INVENTORY = _MODULE.WB_INVENTORY


def _contract(test, result):
    test.assertEqual(tuple(result), _KEYS)
    test.assertEqual(result["caseId"], "TC-P020-04")
    test.assertNotIn(result["decision"], {"qualified", "allowed"})
    test.assertIsInstance(result["reasons"], list)
    test.assertTrue(result["reasons"])
    test.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
    for key in ("rejectedClaims", "preservedResults", "openQuestions"):
        test.assertIsInstance(result[key], list)
        test.assertTrue(all(isinstance(item, str) for item in result[key]))


def _inventory(test, result):
    for item in _INVENTORY:
        test.assertIn(item, result["preservedResults"])


def payload(**overrides):
    base = {
        "consumer": "scopes",
        "sourceHealthy": True,
        "blocksSourceCapture": False,
        "sourceTiming": "source-clock-a",
        "monitoringDropped": True,
    }
    base.update(overrides)
    return base


class TcP02004(unittest.TestCase):
    def test_module_encodes_the_case_text(self):
        self.assertIn("source acquisition", _MODULE.INTERVENTION)
        self.assertIn("stale monitoring", _MODULE.EXPECTED)
        self.assertIn("cosmetic consumer", _MODULE.NEGATIVE)
        for name in ("scopes", "depth_inference", "thumbnail_generation", "detached_display_surface"):
            self.assertIn(name, _MODULE.REPEATS)

    def test_scopes_drop_monitoring_and_keep_timing(self):
        result = evaluate(payload())
        _contract(self, result)
        self.assertEqual(result["decision"], "monitoring_reduced")
        self.assertIn("source.timing:source-clock-a", result["preservedResults"])
        _inventory(self, result)
        self.assertTrue(any("scopes" in item for item in result["reasons"]))

    def test_depth_inference_also_drops_stale_work(self):
        result = evaluate(payload(consumer="depth_inference", sourceTiming="source-clock-b"))
        _contract(self, result)
        self.assertEqual(result["decision"], "monitoring_reduced")
        self.assertIn("source.timing:source-clock-b", result["preservedResults"])
        _inventory(self, result)

    def test_thumbnail_that_blocks_source_is_rejected(self):
        result = evaluate(payload(consumer="thumbnail_generation", blocksSourceCapture=True))
        _contract(self, result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "monitoring_reduced"})
        self.assertEqual(result["rejectedClaims"], ["cosmetic-consumer-blocks-source"])
        self.assertIn("source.timing:source-clock-a", result["preservedResults"])
        _inventory(self, result)

    def test_detached_surface_without_a_healthy_source_is_withheld(self):
        result = evaluate(payload(consumer="detached_display_surface", sourceHealthy=False, monitoringDropped=False))
        self.assertEqual(result["decision"], "withheld")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        _inventory(self, result)

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [None, {**valid, "consumer": "histogram"}, {**valid, "monitoringDropped": 1}]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
