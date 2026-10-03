"""TC-P026-02 equal numbers in one unit are not a shared clock."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p026_tc02", Path(__file__).resolve().parents[1] / "gates" / "p026_tc02.py"
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
        "leftUnit": "ns",
        "rightUnit": "ns",
        "leftOrigin": "sensor-boot",
        "rightOrigin": "audio-boot",
        "leftTimestamp": "1000000000",
        "rightTimestamp": "1000000000",
        "mappingDocumented": False,
        "claimsEquivalenceFromUnits": True,
    }
    base.update(overrides)
    return base


class TcP02602(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P026-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_module_encodes_the_case_text(self):
        self.assertIn("clock domain", _MODULE.INTERVENTION)
        self.assertIn("missing mapping", _MODULE.EXPECTED)
        self.assertIn("numeric units", _MODULE.NEGATIVE)
        self.assertIn("sensor", _MODULE.DOMAINS)
        self.assertIn("encoded_presentation", _MODULE.DOMAINS)

    def test_sensor_and_audio_hardware_nanoseconds_are_not_equivalent(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["unit-equivalence"])
        self.assertEqual(
            result["preservedResults"],
            ["sensor:1000000000", "audio_hardware:1000000000"],
        )
        self.assertTrue(any("sensor" in item and "audio_hardware" in item for item in result["reasons"]))

    def test_monotonic_and_encoded_presentation_are_not_equivalent(self):
        result = evaluate(
            payload(
                leftDomain="monotonic_system",
                rightDomain="encoded_presentation",
                leftOrigin="monotonic",
                rightOrigin="pts",
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(
            result["preservedResults"],
            ["monotonic_system:1000000000", "encoded_presentation:1000000000"],
        )

    def test_missing_mapping_is_timing_unverified(self):
        result = evaluate(payload(claimsEquivalenceFromUnits=False))
        self.assertEqual(result["decision"], "timing_unverified")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("sensor:1000000000", result["preservedResults"])
        self.assertTrue(any("not subtracted" in item for item in result["reasons"]))

    def test_a_recorded_mapping_is_not_clock_equivalence(self):
        result = evaluate(payload(mappingDocumented=True, claimsEquivalenceFromUnits=False))
        self.assertEqual(result["decision"], "mapping_recorded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(any("not subtracted" in item for item in result["reasons"]))
        self.assertIn("audio_hardware:1000000000", result["preservedResults"])

    def test_changed_origin_inside_one_domain_is_not_equivalence(self):
        result = evaluate(
            payload(
                rightDomain="sensor",
                rightOrigin="sensor-rebased",
                claimsEquivalenceFromUnits=True,
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("unit-equivalence", result["rejectedClaims"])
        self.assertEqual(
            result["preservedResults"],
            ["sensor:1000000000", "sensor:1000000000"],
        )

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "leftDomain": "camera"},
            {**valid, "leftTimestamp": "01"},
            {**valid, "leftUnit": "ms"},
            {k: v for k, v in valid.items() if k != "rightTimestamp"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
