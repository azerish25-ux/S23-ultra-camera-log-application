"""TC-P022-04 a stalled preview consumer must not block the source."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p022_tc04", Path(__file__).resolve().parents[1] / "gates" / "p022_tc04.py"
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
_HASH = "cm-preview-stall"
_TIMES = ["t0", "t1", "t2"]


def payload(**overrides):
    base = {
        "consumer": "scopes",
        "sourceHealthy": True,
        "dropsStaleMonitoring": True,
        "sourceTimingIntact": True,
        "resourcesExhausted": False,
        "blocksSourceCapture": False,
        "sourceTimestamps": list(_TIMES),
        "cleanMasterHash": _HASH,
    }
    base.update(overrides)
    return base


class TcP02204(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P022-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_module_encodes_the_case_text(self):
        self.assertIn("source acquisition remains healthy", _MODULE.INTERVENTION)
        self.assertIn("stale monitoring", _MODULE.EXPECTED)
        self.assertIn("irreplaceable source capture", _MODULE.NEGATIVE)

    def test_scopes_drop_stale_work_and_keep_timestamps(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "monitoring_reduced")
        self.assertEqual(result["preservedResults"], _TIMES + [_HASH])
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(any("scopes" in item for item in result["reasons"]))

    def test_depth_inference_stall_also_leaves_source_timing(self):
        result = evaluate(payload(consumer="depth_inference"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "monitoring_reduced")
        self.assertEqual(result["preservedResults"], ["t0", "t1", "t2", _HASH])
        self.assertTrue(any("depth_inference" in item for item in result["reasons"]))
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_thumbnail_that_blocks_the_source_is_rejected(self):
        result = evaluate(payload(consumer="thumbnail", blocksSourceCapture=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "monitoring_reduced"})
        self.assertIn("cosmetic-consumer-blocks-source", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"], _TIMES + [_HASH])

    def test_detached_display_that_corrupts_timing_keeps_the_times(self):
        result = evaluate(
            payload(consumer="detached_display", sourceTimingIntact=False, resourcesExhausted=True)
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("source-timing-corrupted", result["rejectedClaims"])
        self.assertIn("capture-resources-exhausted", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"], _TIMES + [_HASH])

    def test_failing_to_drop_stale_scopes_is_rejected(self):
        result = evaluate(payload(dropsStaleMonitoring=False))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("stale-monitoring-retained", result["rejectedClaims"])
        self.assertIn("t0", result["preservedResults"])

    def test_unhealthy_source_is_withheld(self):
        result = evaluate(payload(sourceHealthy=False, consumer="thumbnail"))
        self.assertEqual(result["decision"], "withheld")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("source acquisition is not healthy", result["openQuestions"])
        self.assertEqual(result["preservedResults"], _TIMES + [_HASH])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "consumer": "encoder"},
            {**valid, "sourceTimestamps": []},
            {**valid, "blocksSourceCapture": 1},
            {**valid, "sourceHealthy": "true"},
            {k: v for k, v in valid.items() if k != "consumer"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
