"""Tests for TC-P145-01."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p145_tc01",
    Path(__file__).resolve().parents[1] / "gates" / "p145_tc01.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    layers = overrides.pop("layers", None)
    base = {
        "evidenceId": "p145-tc01",
        "repeat": "emulator-only",
        "environment": "emulator-only",
        "requiresEvidence": [],
    }
    base.update(_GATE.layer_fields(layers))
    base.update(overrides)
    return base


class TCP14501(unittest.TestCase):
    def assert_contract(self, result, evidence="p145-tc01"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P145-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_case_text_matches_the_spec(self):
        self.assertEqual(_MODULE.CASE["name"], "Skipped test laundering")
        self.assertEqual(_MODULE.CASE["negative"], "Counting skips as passes must fail.")
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "counting-skips-as-passes")

    def test_emulator_only_keeps_categories_visible(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        summary = result["preservedResults"][1]
        self.assertEqual(summary["totalPassed"], 5)
        self.assertEqual(summary["totalSkipped"], 1)
        self.assertEqual(set(summary["layers"]), set(_GATE.LAYERS))
        seen = set()
        for layer in summary["layers"].values():
            for category in ("passed", "failed", "skipped"):
                if layer[category] > 0:
                    seen.add(category)
        self.assertEqual(seen, {"passed", "failed", "skipped"})
        self.assertIn("gpu-color", summary["layers"]["gpu"]["failedIds"])
        self.assertIn("physical-ten-bit-codec", summary["layers"]["physical"]["skippedIds"])

    def test_physical_codec_unavailable_is_not_a_pass(self):
        result = evaluate(payload(repeat="physical-codec-unavailable", environment="physical-codec-unavailable"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["preservedResults"][1]["layers"]["physical"]["status"], "unavailable")
        self.assertEqual(result["preservedResults"][1]["layers"]["physical"]["passed"], 0)

    def test_gpu_unavailable_environment_records_the_skip(self):
        layers = _GATE.fixture_layers()
        layers["gpu"] = [{"id": "gpu-color", "outcome": "skipped"}]
        layers["android"] = [{"id": "android-integration", "outcome": "failed"}]
        result = evaluate(payload(
            layers=layers,
            repeat="gpu-unavailable",
            environment="gpu-unavailable",
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        summary = result["preservedResults"][1]
        self.assertEqual(summary["layers"]["gpu"]["status"], "unavailable")
        self.assertEqual(summary["layers"]["gpu"]["passed"], 0)
        self.assertEqual(summary["totalPassed"], 3)
        self.assertEqual(summary["totalSkipped"], 2)
        self.assertNotEqual(summary["totalPassed"], 5)

    def test_release_passed_including_skipped_is_rejected(self):
        result = evaluate(payload(releasePassed=6))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_GATE.RELEASE_PASSED_INCLUDES_SKIPPED, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertEqual(result["preservedResults"][1]["totalPassed"], 5)

    def test_skipped_added_into_passed_is_rejected(self):
        layers = _GATE.fixture_layers()
        layers["physical"] = {
            "tests": [{"id": "physical-ten-bit-codec", "outcome": "skipped"}],
            "passed": 1,
            "failed": 0,
            "skipped": 0,
        }
        result = evaluate(payload(layers=layers))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_GATE.SKIPPED_ADDED_INTO_PASSED, result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][1]["layers"]["physical"]["passed"], 0)

    def test_claim_that_needs_failing_or_missing_evidence_is_blocked(self):
        failing = evaluate(payload(requiresEvidence=["gpu-color"]))
        self.assert_contract(failing)
        self.assertEqual(failing["decision"], "rejected")
        self.assertIn(_MODULE.CLAIM_BLOCKED, failing["rejectedClaims"])
        missing = evaluate(payload(requiresEvidence=["physical-ten-bit-codec"]))
        self.assertEqual(missing["decision"], "rejected")
        self.assertIn(_MODULE.CLAIM_BLOCKED, missing["rejectedClaims"])
        self.assertIn("p145-tc01", missing["preservedResults"])

    def test_gpu_unavailable_with_a_gpu_pass_is_rejected(self):
        layers = _GATE.fixture_layers()
        layers["gpu"] = [
            {"id": "gpu-color", "outcome": "skipped"},
            {"id": "gpu-parity", "outcome": "passed"},
        ]
        result = evaluate(payload(layers=layers, environment="gpu-unavailable", repeat="gpu-unavailable"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("gpu-unavailable-misclassified", result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p145-tc01-physical-codec"
        result = evaluate(payload(
            evidenceId=evidence,
            repeat="physical-codec-unavailable",
            environment="physical-codec-unavailable",
        ))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(environment="device"))
