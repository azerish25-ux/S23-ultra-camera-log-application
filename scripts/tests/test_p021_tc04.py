"""TC-P021-04 preview consumer stalls."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p021_tc04", Path(__file__).resolve().parents[1] / "gates" / "p021_tc04.py"
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
        "blocksSourceCapture": False,
        "sourceTiming": "pts:1000",
        "monitoringDropped": True,
    }
    base.update(overrides)
    return base


class TcP02104(unittest.TestCase):
    def assertContract(self, result, timing="pts:1000"):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P021-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        for token in _MODULE.FOCUS_INVENTORY:
            self.assertIn(token, result["preservedResults"])
        self.assertIn("source.timing:" + timing, result["preservedResults"])

    def test_module_encodes_intervention_expected_and_negative(self):
        self.assertIn("source acquisition remains healthy", _MODULE.INTERVENTION)
        self.assertIn("without corrupting source timing", _MODULE.EXPECTED)
        self.assertIn("blocks irreplaceable source capture", _MODULE.NEGATIVE)
        for name in ("scopes", "depth_inference", "thumbnail_generation", "detached_display_surface"):
            self.assertIn(name, _MODULE.REPEATS)

    def test_repeat_scopes_drops_monitoring_and_keeps_timing(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "monitoring_reduced")
        self.assertTrue(any("scopes" in item for item in result["reasons"]))
        self.assertTrue(any("source timing unchanged" in item for item in result["reasons"]))

    def test_repeat_depth_inference_drops_monitoring(self):
        result = evaluate(payload(consumer="depth_inference", sourceTiming="pts:2400"))
        self.assertContract(result, "pts:2400")
        self.assertEqual(result["decision"], "monitoring_reduced")
        self.assertIn("source.timing:pts:2400", result["preservedResults"])
        self.assertIn("virtual.subject:face", result["preservedResults"])

    def test_repeat_thumbnail_and_detached_surface(self):
        for consumer in ("thumbnail_generation", "detached_display_surface"):
            result = evaluate(payload(consumer=consumer))
            self.assertContract(result)
            self.assertEqual(result["decision"], "monitoring_reduced")
            self.assertTrue(any(consumer in item for item in result["reasons"]))

    def test_negative_blocking_consumer_keeps_source_timing(self):
        result = evaluate(payload(consumer="depth_inference", blocksSourceCapture=True, monitoringDropped=False))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "monitoring_reduced"})
        self.assertIn("cosmetic-consumer-blocks-source", result["rejectedClaims"])
        self.assertIn("source.timing:pts:1000", result["preservedResults"])
        self.assertIn("physical.distance:unknown", result["preservedResults"])

    def test_negative_scopes_block_does_not_qualify_capture(self):
        result = evaluate(payload(blocksSourceCapture=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("source.timing:pts:1000", result["preservedResults"])

    def test_unhealthy_source_is_withheld(self):
        result = evaluate(payload(sourceHealthy=False, monitoringDropped=True))
        self.assertEqual(result["decision"], "withheld")
        self.assertIn("source acquisition is not healthy", result["openQuestions"])
        self.assertIn("source.timing:pts:1000", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {**valid, "consumer": "overlay"},
            {**valid, "sourceTiming": ""},
            {**valid, "monitoringDropped": "yes"},
            {**valid, "blocksSourceCapture": 1},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
