"""Tests for TC-P104-08."""

from __future__ import annotations

import importlib.util
import unittest
from decimal import Decimal
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "p104_tc08",
    Path(__file__).resolve().parents[1] / "gates" / "p104_tc08.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p104-tc08",
        "condition": "warm",
        "fps": 24,
        "capture_ms": 20,
        "inference_ms": 4,
        "render_ms": 20,
        "encode_ms": 10,
        "dropped_frames": 2,
        "hide_dropped_frames": False,
        "live_depth": "deferred_only",
        "frame_rate_source": "integrated",
        "thermal": "warm",
        "memory": "nominal",
    }
    base.update(overrides)
    return base


class TCP10408(unittest.TestCase):
    def assert_contract(self, result, evidence="p104-tc08"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P104-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertEqual(result["openQuestions"][0], "physical S23 measurement was not run")
        self.assertTrue(any(item.startswith("dropped-frames:") for item in result["preservedResults"]))

    def test_budget_math(self):
        self.assertEqual(_MODULE.integrated_total_ms(20, 4, 20, 10), Decimal(54))
        self.assertEqual(_MODULE.frame_interval_ms(24), Decimal(1000) / Decimal(24))
        self.assertGreater(Decimal(54), Decimal(1000) / Decimal(24))

    def test_good_deferred_policy_retains_dropped_frames(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("total-ms:54", result["preservedResults"])
        self.assertIn("inference-ms:4", result["preservedResults"])
        self.assertIn("over-budget:true", result["preservedResults"])
        self.assertIn("over-budget-fraction:1", result["preservedResults"])
        self.assertIn("dropped-frames:2", result["preservedResults"])
        self.assertIn("frame-rate-source:integrated", result["preservedResults"])
        self.assertNotIn("total-ms:4", result["preservedResults"])

    def test_negative_inference_fps_and_severe_live(self):
        inferred = evaluate(payload(frame_rate_source="inference"))
        self.assertEqual(inferred["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, inferred["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, inferred["reasons"])
        self.assertIn("total-ms:54", inferred["preservedResults"])
        self.assertIn("inference-ms:4", inferred["preservedResults"])
        self.assertIn("dropped-frames:2", inferred["preservedResults"])
        severe = evaluate(payload(condition="severe-thermal", thermal="severe", live_depth="live", dropped_frames=4))
        self.assertEqual(severe["decision"], "rejected")
        self.assertIn("live-under-severe", severe["rejectedClaims"])
        self.assertIn("dropped-frames:4", severe["preservedResults"])
        hidden = evaluate(payload(hide_dropped_frames=True, dropped_frames=9))
        self.assertIn("hidden-dropped-frames", hidden["rejectedClaims"])
        self.assertIn("dropped-frames:9", hidden["preservedResults"])

    def test_evidence_change_repeats_conditions(self):
        evidence = "p104-tc08-cold"
        cold = evaluate(payload(evidenceId=evidence, condition="cold", thermal="nominal"))
        self.assert_contract(cold, evidence)
        self.assertEqual(cold["decision"], "recorded")
        pressure = evaluate(
            payload(condition="memory-pressure", memory="pressure", live_depth="lower_cost_preview")
        )
        self.assertEqual(pressure["decision"], "recorded")
        self.assertIn("condition:memory-pressure", pressure["preservedResults"])
        deferred = evaluate(payload(condition="severe-thermal", thermal="severe", memory="severe"))
        self.assertEqual(deferred["decision"], "recorded")
        self.assertIn("thermal:severe", deferred["preservedResults"])
        self.assertIn("dropped-frames:2", deferred["preservedResults"])

    def test_invalid_payload_raises(self):
        cases = (
            {},
            {**payload(), "applyNegative": True},
            payload(condition="hot"),
            payload(fps=0),
            payload(capture_ms=-1),
            payload(dropped_frames=-1),
            payload(condition="severe-thermal", thermal="warm"),
            payload(live_depth="qualified"),
            payload(inference_ms=float("nan")),
        )
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
