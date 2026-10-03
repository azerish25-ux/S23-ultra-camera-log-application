"""TC-P025-08 physical sync disagreement."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p025_tc08", Path(__file__).resolve().parents[1] / "gates" / "p025_tc08.py"
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
_CONTAINER = "container:video=0,audio=0"


def payload(**overrides):
    base = {
        "position": "beginning",
        "fixtureDistanceM": "1.5",
        "packetStartsAligned": True,
        "visibleAudibleOffsetMs": "40",
        "drift": False,
        "packetOnlyCertificate": False,
        "containerTiming": _CONTAINER,
    }
    base.update(overrides)
    return base


class TcP02508(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P025-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def assert_distinct(self, result, physical):
        self.assertEqual(result["preservedResults"][0], _CONTAINER)
        self.assertEqual(result["preservedResults"][1], physical)
        self.assertNotEqual(result["preservedResults"][0], result["preservedResults"][1])

    def test_beginning_offset_fails_sync_and_keeps_container_timing(self):
        result = evaluate(payload(position="beginning", fixtureDistanceM="1.5"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "sync_failed")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("physical-sync", result["rejectedClaims"])
        self.assert_distinct(result, "physical:beginning:40ms:distance=1.5")
        self.assertTrue(any("distinct results" in item for item in result["reasons"]))
        self.assertTrue(any("aligned packet starts" in item for item in result["reasons"]))

    def test_end_offset_with_documented_distance_fails_sync(self):
        result = evaluate(
            payload(position="end", fixtureDistanceM="3", visibleAudibleOffsetMs="15")
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "sync_failed")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assert_distinct(result, "physical:end:15ms:distance=3")
        self.assertIn("physical-sync", result["rejectedClaims"])

    def test_middle_drift_is_not_container_agreement(self):
        result = evaluate(
            payload(
                position="middle",
                fixtureDistanceM="2.5",
                visibleAudibleOffsetMs="0",
                drift=True,
            )
        )
        self.assertEqual(result["decision"], "sync_failed")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("physical-drift", result["rejectedClaims"])
        self.assert_distinct(result, "physical:middle:0ms:distance=2.5")

    def test_negative_packet_only_certificate_fails(self):
        result = evaluate(
            payload(
                packetOnlyCertificate=True,
                visibleAudibleOffsetMs="0",
                drift=False,
                packetStartsAligned=True,
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "sync_failed"})
        self.assertIn("packet-only-lip-sync-certificate", result["rejectedClaims"])
        self.assert_distinct(result, "physical:beginning:0ms:distance=1.5")
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_zero_offset_without_a_certificate_stays_withheld(self):
        result = evaluate(payload(visibleAudibleOffsetMs="0", drift=False))
        self.assertEqual(result["decision"], "withheld")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assert_distinct(result, "physical:beginning:0ms:distance=1.5")
        self.assertEqual(result["openQuestions"], ["physical synchronization unverified on host"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "position": "start"},
            {**valid, "fixtureDistanceM": "0"},
            {**valid, "fixtureDistanceM": "1.50"},
            {**valid, "visibleAudibleOffsetMs": "40.0"},
            {**valid, "containerTiming": ""},
            {**valid, "packetStartsAligned": "true"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
