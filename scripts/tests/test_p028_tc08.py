"""TC-P028-08 packet alignment is not a lip-sync certificate."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p028_tc08", Path(__file__).resolve().parents[1] / "gates" / "p028_tc08.py"
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
_CONTAINER = "container:pts-aligned"


def payload(**overrides):
    base = {
        "position": "beginning",
        "fixtureDistanceM": "1.5",
        "packetStartsAligned": True,
        "visibleAudibleOffsetMs": "80",
        "drift": False,
        "packetOnlyCertificate": False,
        "containerTiming": _CONTAINER,
    }
    base.update(overrides)
    return base


class TcP02808(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P028-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_module_encodes_the_case_text(self):
        self.assertIn("visible-audible", _MODULE.INTERVENTION)
        self.assertIn("distinct results", _MODULE.EXPECTED)
        self.assertIn("packet-only", _MODULE.NEGATIVE)
        self.assertEqual(_MODULE._POSITIONS, ("beginning", "middle", "end"))

    def test_beginning_offset_fails_sync_and_keeps_both_results(self):
        result = evaluate(payload(position="beginning", fixtureDistanceM="1.5"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "sync_failed")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("physical-sync", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][0], _CONTAINER)
        self.assertEqual(result["preservedResults"][1], "physical:beginning:80ms:distance=1.5")
        self.assertNotEqual(result["preservedResults"][0], result["preservedResults"][1])

    def test_middle_drift_fails_the_sync_gate(self):
        result = evaluate(
            payload(
                position="middle",
                fixtureDistanceM="2",
                visibleAudibleOffsetMs="0",
                drift=True,
            )
        )
        self.assertEqual(result["decision"], "sync_failed")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("physical-drift", result["rejectedClaims"])
        self.assertIn(_CONTAINER, result["preservedResults"])
        self.assertIn("physical:middle:0ms:distance=2", result["preservedResults"])

    def test_end_packet_only_certificate_is_rejected(self):
        result = evaluate(
            payload(
                position="end",
                fixtureDistanceM="3.5",
                visibleAudibleOffsetMs="0",
                drift=False,
                packetOnlyCertificate=True,
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "sync_failed"})
        self.assertIn("packet-only-lip-sync-certificate", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][0], _CONTAINER)
        self.assertEqual(result["preservedResults"][1], "physical:end:0ms:distance=3.5")

    def test_packet_only_certificate_with_an_offset_is_rejected(self):
        result = evaluate(
            payload(
                position="end",
                fixtureDistanceM="3.5",
                visibleAudibleOffsetMs="-40",
                packetOnlyCertificate=True,
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("packet-only-lip-sync-certificate", result["rejectedClaims"])
        self.assertIn("physical-sync", result["rejectedClaims"])
        self.assertIn(_CONTAINER, result["preservedResults"])
        self.assertIn("physical:end:-40ms:distance=3.5", result["preservedResults"])

    def test_zero_offset_without_a_certificate_is_withheld(self):
        result = evaluate(
            payload(
                position="beginning",
                fixtureDistanceM="1.5",
                visibleAudibleOffsetMs="0",
                drift=False,
            )
        )
        self.assertEqual(result["decision"], "withheld")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "sync_failed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn(_CONTAINER, result["preservedResults"])
        self.assertIn("physical:beginning:0ms:distance=1.5", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {**valid, "position": "start"},
            {**valid, "fixtureDistanceM": "1.50"},
            {**valid, "visibleAudibleOffsetMs": "08"},
            {**valid, "containerTiming": "physical:beginning:80ms:distance=1.5"},
            {k: v for k, v in valid.items() if k != "drift"},
            {**valid, "extra": True},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
