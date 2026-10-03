"""TC-P068-06 critical-path resource contention."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p068_tc06", Path(__file__).resolve().parents[1] / "gates" / "p068_tc06.py"
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
        "workload": "inference",
        "contention": True,
        "hiddenSourceDrops": False,
        "previewSmooth": True,
        "monitoringDegraded": True,
        "sourceRetained": True,
        "stoppedHonestly": False,
    }
    base.update(overrides)
    return base


class TcP06806(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P068-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_packet_strings(self):
        self.assertIn("preview smoothness", _MODULE.NEGATIVE)
        self.assertIn("thumbnails", _MODULE.REPEAT)

    def test_monitoring_degrades_before_the_source(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "monitoring_degraded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("workload:inference", result["preservedResults"])
        self.assertIn("source:true", result["preservedResults"])

    def test_hidden_source_drops_fail(self):
        result = evaluate(payload(hiddenSourceDrops=True, previewSmooth=True, stoppedHonestly=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["hidden-source-drops"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("workload:inference", result["preservedResults"])
        self.assertIn("source:true", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "monitoring_degraded", "stopped_honestly"})

    def test_honest_stop_is_not_a_hidden_drop(self):
        result = evaluate(payload(monitoringDegraded=False, sourceRetained=False, stoppedHonestly=True))
        self.assertEqual(result["decision"], "stopped_honestly")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("stopped:true", result["preservedResults"])
        self.assertIn("workload:inference", result["preservedResults"])

    def test_repeat_scopes_and_denoise(self):
        scopes = evaluate(payload(workload="scopes"))
        denoise = evaluate(payload(workload="denoise"))
        self.assertEqual(scopes["decision"], "monitoring_degraded")
        self.assertEqual(denoise["decision"], "monitoring_degraded")
        self.assertIn("workload:scopes", scopes["preservedResults"])
        self.assertIn("workload:denoise", denoise["preservedResults"])

    def test_repeat_thumbnails_and_background_io(self):
        thumbs = evaluate(payload(workload="thumbnails"))
        files = evaluate(payload(workload="background-io", contention=False, monitoringDegraded=False))
        self.assertEqual(thumbs["decision"], "monitoring_degraded")
        self.assertEqual(files["decision"], "source_retained")
        self.assertIn("workload:thumbnails", thumbs["preservedResults"])
        self.assertIn("workload:background-io", files["preservedResults"])
        self.assertIn("source:true", files["preservedResults"])

    def test_lost_source_without_a_stop_is_rejected(self):
        result = evaluate(payload(sourceRetained=False, monitoringDegraded=False))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["source-contract-lost"])
        self.assertIn("workload:inference", result["preservedResults"])
        self.assertIn("source:false", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "workload": "capture"},
            {**valid, "hiddenSourceDrops": "false"},
            {**valid, "extra": True},
            {k: v for k, v in valid.items() if k != "contention"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
