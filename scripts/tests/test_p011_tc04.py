"""TC-P011-04 a marketing model name does not refresh a stale timing cache."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p011_tc04", Path(__file__).resolve().parents[1] / "gates" / "p011_tc04.py"
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


def rate(numerator=15, denominator=1):
    return {"numerator": numerator, "denominator": denominator}


def payload(**overrides):
    base = {
        "cached": {
            "tupleId": "rear-15-30",
            "buildFingerprint": "build-a",
            "codecIdentity": "hevc-a",
            "probeProtocol": "probe-1",
        },
        "current": {
            "buildFingerprint": "build-b",
            "codecIdentity": "hevc-a",
            "probeProtocol": "probe-1",
        },
        "marketingModel": "SM-S911",
        "variant": "build_changed",
        "aeMin": rate(15),
        "aeMax": rate(30),
        "requestedFps": rate(24),
        "containerTimestampsAssigned": True,
    }
    base.update(overrides)
    return base


class TcP01104(unittest.TestCase):
    def assert_contract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P011-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "native_fixed_24"})
        self.assertTrue(result["reasons"])

    def test_encodes_intervention_expected_and_negative(self):
        self.assertIn("cached probe", _MODULE.INTERVENTION)
        self.assertIn("historical evidence", _MODULE.EXPECTED)
        self.assertIn("marketing-model-name", _MODULE.NEGATIVE)

    def test_build_change_requalifies_and_keeps_history(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "requalify")
        self.assertIn("cache-hit", result["rejectedClaims"])
        self.assertIn("native-fixed-24", result["rejectedClaims"])
        self.assertEqual(
            result["preservedResults"][:3],
            ["historical:rear-15-30", "ae:15/1-30/1", "requested:24/1"],
        )
        self.assertTrue(any("SM-S911" in item and "does not bypass" in item for item in result["reasons"]))
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_codec_software_change_with_same_marketing_name(self):
        current = {
            "buildFingerprint": "build-a",
            "codecIdentity": "hevc-b",
            "probeProtocol": "probe-1",
        }
        cached = {
            "tupleId": "rear-15-30",
            "buildFingerprint": "build-a",
            "codecIdentity": "hevc-a",
            "probeProtocol": "probe-1",
        }
        result = evaluate(payload(cached=cached, current=current, variant="codec_changed"))
        self.assertEqual(result["decision"], "requalify")
        self.assertIn("historical:rear-15-30", result["preservedResults"])
        self.assertTrue(any("codec identity change" in item for item in result["reasons"]))
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_probe_protocol_change_requalifies(self):
        current = {
            "buildFingerprint": "build-a",
            "codecIdentity": "hevc-a",
            "probeProtocol": "probe-2",
        }
        cached = {
            "tupleId": "rear-15-30",
            "buildFingerprint": "build-a",
            "codecIdentity": "hevc-a",
            "probeProtocol": "probe-1",
        }
        result = evaluate(
            payload(
                cached=cached,
                current=current,
                variant="protocol_changed",
                containerTimestampsAssigned=False,
            )
        )
        self.assertEqual(result["decision"], "requalify")
        self.assertEqual(result["rejectedClaims"], ["cache-hit"])
        self.assertIn("probe-protocol identity change", " ".join(result["reasons"]))
        self.assertIn("ae:15/1-30/1", result["preservedResults"])

    def test_unchanged_identities_match_without_using_the_model_name(self):
        current = {
            "buildFingerprint": "build-a",
            "codecIdentity": "hevc-a",
            "probeProtocol": "probe-1",
        }
        cached = {"tupleId": "rear-15-30", **current}
        result = evaluate(
            payload(
                cached=cached,
                current=current,
                variant="unchanged",
                marketingModel="Galaxy S23",
                containerTimestampsAssigned=False,
            )
        )
        self.assertEqual(result["decision"], "cache_matches")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("rear-15-30", result["preservedResults"])
        self.assertTrue(any("marketing model name was not used" in item for item in result["reasons"]))

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {**valid, "variant": "renamed"},
            {**valid, "marketingModel": "  "},
            {**valid, "cached": {"tupleId": "x"}},
            {**valid, "aeMin": {"numerator": 48, "denominator": 2}},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
