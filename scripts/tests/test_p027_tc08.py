"""TC-P027-08 packet alignment is not a lip-sync certificate."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p027_tc08", Path(__file__).resolve().parents[1] / "gates" / "p027_tc08.py"
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
        "packetStartsAligned": True,
        "measuredOffsetMs": 40,
        "fixtureDistance": "1.5m",
        "packetOnlyCertificate": False,
        "containerTiming": "container-start-aligned",
        "physicalSync": "visible-audible-offset",
    }
    base.update(overrides)
    return base


class TcP02708(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P027-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_module_encodes_the_case_text(self):
        self.assertIn("visible-audible", _MODULE.INTERVENTION)
        self.assertIn("distinct results", _MODULE.EXPECTED)
        self.assertIn("packet-only", _MODULE.NEGATIVE)
        self.assertIn("beginning", _MODULE.POSITIONS)
        self.assertIn("middle", _MODULE.POSITIONS)
        self.assertIn("end", _MODULE.POSITIONS)

    def test_beginning_offset_fails_sync_and_keeps_both_results(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "sync_failed")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(
            result["preservedResults"],
            ["container-start-aligned", "visible-audible-offset", "1.5m", "beginning"],
        )
        self.assertNotEqual(result["preservedResults"][0], result["preservedResults"][1])
        self.assertTrue(any("aligned packet starts" in item for item in result["reasons"]))

    def test_middle_of_take_is_a_separate_repeat(self):
        result = evaluate(payload(position="middle", fixtureDistance="2m", measuredOffsetMs=15))
        self.assertContract(result)
        self.assertEqual(result["decision"], "sync_failed")
        self.assertIn("2m", result["preservedResults"])
        self.assertIn("middle", result["preservedResults"])
        self.assertIn("container-start-aligned", result["preservedResults"])
        self.assertIn("visible-audible-offset", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_packet_only_certificate_is_rejected_at_the_end(self):
        result = evaluate(
            payload(position="end", fixtureDistance="3.25m", packetOnlyCertificate=True, measuredOffsetMs=0)
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "sync_failed"})
        self.assertEqual(result["rejectedClaims"], ["packet-only-lipsync"])
        self.assertEqual(
            result["preservedResults"],
            ["container-start-aligned", "visible-audible-offset", "3.25m", "end"],
        )

    def test_zero_offset_without_a_certificate_is_withheld(self):
        result = evaluate(payload(measuredOffsetMs=0, packetStartsAligned=True))
        self.assertEqual(result["decision"], "withheld")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "sync_failed"})
        self.assertIn("container-start-aligned", result["preservedResults"])
        self.assertIn("visible-audible-offset", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {**valid, "position": "start"},
            {**valid, "fixtureDistance": "1.5"},
            {**valid, "measuredOffsetMs": -1},
            {**valid, "measuredOffsetMs": True},
            {**valid, "containerTiming": "visible-audible-offset", "physicalSync": "visible-audible-offset"},
            {**valid, "packetOnlyCertificate": "false"},
            {k: v for k, v in valid.items() if k != "physicalSync"},
            {**valid, "extra": True},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
