"""TC-P030-02 timestamp domain confusion."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p030_tc02", Path(__file__).resolve().parents[1] / "gates" / "p030_tc02.py"
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
        "leftDomain": "sensor",
        "rightDomain": "audio_hardware",
        "leftUnits": "ns",
        "rightUnits": "ns",
        "leftValue": "1000000000",
        "rightValue": "1000000000",
        "leftOrigin": "sensor-boot",
        "rightOrigin": "audio-boot",
        "mappingMethod": "none",
        "retainedSamples": 0,
    }
    base.update(overrides)
    return base


class TcP03002(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P030-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_sensor_timestamp_with_changed_origin_stays_unverified(self):
        source = payload(leftDomain="sensor", rightDomain="audio_hardware")
        result = evaluate(source)
        self.assertContract(result)
        self.assertEqual(result["decision"], "unverified")
        self.assertIn("numeric-unit-equivalence", result["rejectedClaims"])
        self.assertIn("origin-changed", result["rejectedClaims"])
        self.assertEqual(
            result["preservedResults"],
            [
                "sensor:sensor-boot:1000000000ns",
                "audio_hardware:audio-boot:1000000000ns",
            ],
        )
        self.assertEqual(result["openQuestions"], ["timing unverified"])
        self.assertNotIn("0", result["preservedResults"])
        self.assertIn("subtracting unrelated clocks", " ".join(result["reasons"]))

    def test_audio_hardware_timestamp_is_not_the_monotonic_clock(self):
        result = evaluate(
            payload(
                leftDomain="audio_hardware",
                rightDomain="monotonic_system",
                leftOrigin="audio-boot",
                rightOrigin="boottime",
                leftValue="4000",
                rightValue="4000",
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "unverified")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("audio_hardware:audio-boot:4000ns", result["preservedResults"])
        self.assertIn("monotonic_system:boottime:4000ns", result["preservedResults"])
        self.assertIn("numeric-unit-equivalence", result["rejectedClaims"])

    def test_monotonic_and_encoded_presentation_values_are_not_subtracted(self):
        result = evaluate(
            payload(
                leftDomain="monotonic_system",
                rightDomain="encoded_presentation",
                leftOrigin="boottime",
                rightOrigin="container-zero",
                leftValue="80",
                rightValue="80",
                leftUnits="us",
                rightUnits="us",
            )
        )
        self.assertEqual(result["decision"], "unverified")
        self.assertIn("monotonic_system:boottime:80us", result["preservedResults"])
        self.assertIn("encoded_presentation:container-zero:80us", result["preservedResults"])
        self.assertNotIn("0", result["preservedResults"])

    def test_negative_matching_nanoseconds_do_not_establish_equivalence(self):
        result = evaluate(
            payload(mappingMethod="numeric_units_only", retainedSamples=8, leftOrigin="same", rightOrigin="same")
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "correspondence_estimated"})
        self.assertEqual(
            result["rejectedClaims"],
            ["numeric-unit-equivalence", "unrelated-domain-subtraction"],
        )
        self.assertIn("sensor:same:1000000000ns", result["preservedResults"])
        self.assertIn("audio_hardware:same:1000000000ns", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_identified_method_keeps_both_origins(self):
        result = evaluate(
            payload(mappingMethod="measured_offset", retainedSamples=2)
        )
        self.assertEqual(result["decision"], "correspondence_estimated")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("sensor:sensor-boot:1000000000ns", result["preservedResults"])
        self.assertIn("audio_hardware:audio-boot:1000000000ns", result["preservedResults"])
        self.assertEqual(result["openQuestions"], ["physical synchronization unverified"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "leftDomain": "sensor", "rightDomain": "sensor"},
            {**valid, "leftValue": 1000000000},
            {**valid, "mappingMethod": "subtract"},
            {**valid, "retainedSamples": -1},
            {**valid, "leftUnits": "nanoseconds"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
