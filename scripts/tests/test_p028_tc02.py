"""TC-P028-02 numeric units do not make clock domains equivalent."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p028_tc02", Path(__file__).resolve().parents[1] / "gates" / "p028_tc02.py"
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
        "leftValue": "1000",
        "rightValue": "1000",
        "leftOrigin": "sensor-boot",
        "rightOrigin": "audio-boot",
        "mappingMethod": "none",
        "retainedSamples": 0,
    }
    base.update(overrides)
    return base


class TcP02802(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P028-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_module_encodes_the_case_text(self):
        self.assertIn("clock domain", _MODULE.INTERVENTION)
        self.assertIn("timing unverified", _MODULE.EXPECTED)
        self.assertIn("numeric units", _MODULE.NEGATIVE)

    def test_sensor_and_audio_hardware_without_mapping_stay_unverified(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "unverified")
        self.assertIn("numeric-unit-equivalence", result["rejectedClaims"])
        self.assertIn("sensor:sensor-boot:1000ns", result["preservedResults"])
        self.assertIn("audio_hardware:audio-boot:1000ns", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_audio_hardware_and_monotonic_units_only_are_rejected(self):
        result = evaluate(
            payload(
                leftDomain="audio_hardware",
                rightDomain="monotonic_system",
                leftOrigin="audio-boot",
                rightOrigin="monotonic-boot",
                mappingMethod="numeric_units_only",
                retainedSamples=4,
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "correspondence_estimated"})
        self.assertIn("numeric-unit-equivalence", result["rejectedClaims"])
        self.assertIn("unrelated-domain-subtraction", result["rejectedClaims"])
        self.assertIn("audio_hardware:audio-boot:1000ns", result["preservedResults"])
        self.assertIn("monotonic_system:monotonic-boot:1000ns", result["preservedResults"])

    def test_monotonic_and_encoded_presentation_need_a_real_method(self):
        result = evaluate(
            payload(
                leftDomain="monotonic_system",
                rightDomain="encoded_presentation",
                leftOrigin="monotonic-boot",
                rightOrigin="pts-origin",
                mappingMethod="measured_offset",
                retainedSamples=2,
            )
        )
        self.assertEqual(result["decision"], "correspondence_estimated")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("monotonic_system:monotonic-boot:1000ns", result["preservedResults"])
        self.assertIn("encoded_presentation:pts-origin:1000ns", result["preservedResults"])

    def test_encoded_presentation_and_sensor_documented_epoch_is_not_equivalence(self):
        result = evaluate(
            payload(
                leftDomain="encoded_presentation",
                rightDomain="sensor",
                leftOrigin="pts-origin",
                rightOrigin="sensor-boot",
                leftUnits="ms",
                rightUnits="ms",
                mappingMethod="documented_epoch",
                retainedSamples=3,
            )
        )
        self.assertEqual(result["decision"], "correspondence_estimated")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(any("does not equate" in item for item in result["reasons"]))
        self.assertIn("encoded_presentation:pts-origin:1000ms", result["preservedResults"])
        self.assertIn("sensor:sensor-boot:1000ms", result["preservedResults"])

    def test_changed_origin_without_mapping_is_unverified(self):
        result = evaluate(
            payload(
                leftDomain="sensor",
                rightDomain="monotonic_system",
                mappingMethod="none",
                retainedSamples=1,
            )
        )
        self.assertEqual(result["decision"], "unverified")
        self.assertIn("origin-changed", result["rejectedClaims"])
        self.assertIn("sensor:sensor-boot:1000ns", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {**valid, "leftDomain": "sensor", "rightDomain": "sensor"},
            {**valid, "mappingMethod": "guess"},
            {**valid, "leftValue": "0100"},
            {**valid, "retainedSamples": -1},
            {k: v for k, v in valid.items() if k != "leftOrigin"},
            {**valid, "extra": True},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
