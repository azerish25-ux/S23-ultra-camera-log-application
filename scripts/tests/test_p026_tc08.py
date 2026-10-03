"""TC-P026-08 packet alignment is not physical synchronization."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p026_tc08", Path(__file__).resolve().parents[1] / "gates" / "p026_tc08.py"
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
        "position": "beginning",
        "fixtureDistance": "1.5m",
        "packetStartAligned": True,
        "containerOffsetMs": 0,
        "measuredOffsetMs": 40,
        "drift": False,
        "packetOnlyCertificate": False,
        "takeId": "take-p026",
    }
    base.update(overrides)
    return base


class TcP02608(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P026-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_module_encodes_the_case_text(self):
        self.assertIn("visible-audible", _MODULE.INTERVENTION)
        self.assertIn("distinct results", _MODULE.EXPECTED)
        self.assertIn("packet-only", _MODULE.NEGATIVE)
        self.assertIn("beginning", _MODULE.POSITIONS)
        self.assertIn("end", _MODULE.POSITIONS)

    def test_beginning_offset_fails_the_sync_gate(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "sync_failed")
        self.assertEqual(result["rejectedClaims"], ["physical-sync"])
        self.assertEqual(
            result["preservedResults"],
            ["container:take-p026:0", "physical:beginning:1.5m:40"],
        )
        self.assertNotEqual(result["preservedResults"][0], result["preservedResults"][1])

    def test_end_offset_keeps_container_and_physical_results_distinct(self):
        result = evaluate(payload(position="end", fixtureDistance="2m", measuredOffsetMs=-15))
        self.assertContract(result)
        self.assertEqual(result["decision"], "sync_failed")
        self.assertIn("physical-sync", result["rejectedClaims"])
        self.assertEqual(
            result["preservedResults"],
            ["container:take-p026:0", "physical:end:2m:-15"],
        )

    def test_middle_packet_only_certificate_fails(self):
        result = evaluate(payload(position="middle", packetOnlyCertificate=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("packet-only-lipsync", result["rejectedClaims"])
        self.assertIn("physical-sync", result["rejectedClaims"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "sync_unverified"})
        self.assertIn("container:take-p026:0", result["preservedResults"])
        self.assertIn("physical:middle:1.5m:40", result["preservedResults"])

    def test_zero_offset_stays_distinct_and_uncertified(self):
        result = evaluate(payload(measuredOffsetMs=0))
        self.assertEqual(result["decision"], "sync_unverified")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(
            result["preservedResults"],
            ["container:take-p026:0", "physical:beginning:1.5m:0"],
        )
        self.assertTrue(any("remain distinct" in item for item in result["reasons"]))

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "position": "start"},
            {**valid, "fixtureDistance": "2.0m"},
            {**valid, "containerOffsetMs": "0"},
            {**valid, "takeId": ""},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
