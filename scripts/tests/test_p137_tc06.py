"""Tests for TC-P137-06."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p137_tc06",
    Path(__file__).resolve().parents[1] / "gates" / "p137_tc06.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def reference(edition, appearance, state="fact", source="src-edition"):
    return {
        "edition": edition,
        "appearance": appearance,
        "state": state,
        "source_id": source,
    }


def payload(**overrides):
    base = {
        "evidenceId": "p137-tc06",
        "repeat": "theatrical",
        "references": [
            reference("theatrical", "warm-print"),
            reference("digital", "cool-video", source="src-digital"),
        ],
        "definitive": None,
    }
    base.update(overrides)
    return base


class TCP13706(unittest.TestCase):
    def assert_contract(self, result, evidence="p137-tc06"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P137-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 capture was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_conflicting_editions_stay_separate(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        detail = result["preservedResults"][1]
        self.assertEqual(detail["distinctAppearances"], 2)
        self.assertIsNone(detail["definitive"])
        self.assertEqual(len(detail["references"]), 2)
        self.assertEqual(detail["stateCounts"]["fact"], 2)
        self.assertEqual(detail["stateCounts"]["unknown"], 0)
        self.assertEqual(tuple(detail["stateCounts"]), _GATE.STATES)
        self.assertEqual(_MODULE.CASE["name"], "Reference edition conflict")

    def test_average_fact_is_rejected(self):
        definitive = _GATE.make_field("definitive_look", "fact", "averaged-look", "src-average")
        result = evaluate(payload(definitive=definitive))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.AVERAGED_EDITIONS, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        detail = result["preservedResults"][1]
        self.assertEqual(detail["definitive"]["state"], "unknown")
        self.assertIsNone(detail["definitive"]["value"])
        self.assertEqual(detail["references"][0]["appearance"], "warm-print")
        self.assertEqual(detail["references"][1]["appearance"], "cool-video")
        self.assertEqual(detail["stateCounts"]["fact"], 2)
        self.assertEqual(detail["stateCounts"]["unknown"], 1)

    def test_numeric_mean_is_not_a_historical_fact(self):
        definitive = _GATE.make_field("definitive_look", "fact", 2, "src-average")
        result = evaluate(payload(
            references=[
                reference("theatrical", 1, source="src-theatrical"),
                reference("hdr", 3, source="src-hdr"),
            ],
            definitive=definitive,
            repeat="HDR",
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.AVERAGED_EDITIONS, result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][1]["definitive"]["state"], "unknown")

    def test_unidentified_reference_stays_unknown(self):
        result = evaluate(payload(
            references=[
                reference("theatrical", "warm-print", source="src-theatrical"),
                reference("unidentified", None, state="unknown", source=None),
            ],
            repeat="unidentified",
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        unknown = result["preservedResults"][1]["references"][1]
        self.assertEqual(unknown["state"], "unknown")
        self.assertIsNone(unknown["appearance"])
        self.assertEqual(result["preservedResults"][1]["stateCounts"]["unknown"], 1)
        self.assertEqual(result["preservedResults"][1]["distinctAppearances"], 1)

    def test_repeat_editions_remain_separate(self):
        result = evaluate(payload(
            references=[
                reference("theatrical", "print-a", source="src-theatrical"),
                reference("digital", "video-b", source="src-digital"),
                reference("hdr", "hdr-c", source="src-hdr"),
                reference("unidentified", None, state="unknown", source=None),
            ],
            repeat="digital",
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        editions = [item["edition"] for item in result["preservedResults"][1]["references"]]
        self.assertEqual(editions, ["theatrical", "digital", "hdr", "unidentified"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(references=[reference("theatrical", "only-one")]))
