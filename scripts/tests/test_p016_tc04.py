"""TC-P016-04 firmware cache staleness."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p016_tc04", Path(__file__).resolve().parents[1] / "gates" / "p016_tc04.py"
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
_ORACLE = ["file-retained", "playback:separate", "cadence:separate"]
_MODEL = "Galaxy S23"


def _payload(
    *,
    build="fp-hw-1",
    codec="codec-a",
    protocol="probe-3",
    current_build=None,
    current_codec=None,
    current_protocol=None,
    stream_id="rear-raw",
    previously_successful=True,
    model=_MODEL,
    variant="unchanged",
):
    return {
        "cached": {
            "streamId": stream_id,
            "buildFingerprint": build,
            "codecIdentity": codec,
            "probeProtocol": protocol,
            "previouslySuccessful": previously_successful,
        },
        "current": {
            "buildFingerprint": build if current_build is None else current_build,
            "codecIdentity": codec if current_codec is None else current_codec,
            "probeProtocol": protocol if current_protocol is None else current_protocol,
        },
        "modelName": model,
        "variant": variant,
    }


class TcP01604(unittest.TestCase):
    def assertContract(self, result, decision):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P016-04")
        self.assertEqual(result["decision"], decision)
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertEqual(result["openQuestions"], ["not-endurance-certified"])
        for token in _ORACLE:
            self.assertIn(token, result["preservedResults"])

    def test_contract_text_is_encoded(self):
        self.assertIn("cached probe", _MODULE.INTERVENTION)
        self.assertIn("historical evidence", _MODULE.EXPECTED)
        self.assertIn("marketing-model-name", _MODULE.NEGATIVE)

    def test_changed_probe_protocol_requires_requalification(self):
        payload = _payload(current_protocol="probe-4", variant="protocol_changed")
        self.assertEqual(payload["cached"]["buildFingerprint"], payload["current"]["buildFingerprint"])
        self.assertEqual(payload["cached"]["codecIdentity"], payload["current"]["codecIdentity"])
        result = evaluate(payload)
        self.assertContract(result, "requalify")
        self.assertEqual(result["rejectedClaims"], ["cache-hit"])
        self.assertEqual(result["preservedResults"], ["historical:rear-raw", *_ORACLE])
        self.assertNotIn("rear-raw", result["preservedResults"])
        self.assertNotIn(_MODEL, json.dumps(result))
        self.assertEqual(
            result["reasons"],
            ["cached probe is historical only after probe-protocol identity change"],
        )

    def test_updated_codec_with_unchanged_hardware_requires_requalification(self):
        payload = _payload(current_codec="codec-b", variant="codec_changed")
        self.assertEqual(payload["cached"]["buildFingerprint"], payload["current"]["buildFingerprint"])
        self.assertNotEqual(payload["cached"]["codecIdentity"], payload["current"]["codecIdentity"])
        result = evaluate(payload)
        self.assertContract(result, "requalify")
        self.assertEqual(result["rejectedClaims"], ["cache-hit"])
        self.assertIn("historical:rear-raw", result["preservedResults"])
        self.assertTrue(any("codec identity change" in reason for reason in result["reasons"]))
        self.assertNotIn(_MODEL, json.dumps(result))

    def test_marketing_model_name_does_not_bypass_build_change(self):
        first = evaluate(_payload(current_build="fp-hw-2", variant="build_changed", model="Galaxy S23"))
        second = evaluate(_payload(current_build="fp-hw-2", variant="build_changed", model="Other Phone"))
        self.assertEqual(first, second)
        self.assertEqual(first["decision"], "requalify")
        self.assertNotIn(first["decision"], {"qualified", "allowed", "cache_current"})
        self.assertEqual(first["rejectedClaims"], ["cache-hit"])
        self.assertNotIn("Galaxy S23", json.dumps(first))
        self.assertNotIn("Other Phone", json.dumps(second))
        self.assertTrue(any("build identity change" in reason for reason in first["reasons"]))

    def test_matching_identity_is_cache_current_not_qualified(self):
        result = evaluate(_payload(variant="unchanged", previously_successful=True))
        self.assertContract(result, "cache_current")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"], ["rear-raw", *_ORACLE])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "requalify"})
        self.assertTrue(any("not a physical S23 qualification" in reason for reason in result["reasons"]))

    def test_matching_unsuccessful_cache_stays_unsuccessful(self):
        result = evaluate(_payload(previously_successful=False))
        self.assertContract(result, "cache_unsuccessful")
        self.assertEqual(result["preservedResults"], ["rear-raw", *_ORACLE])
        self.assertEqual(result["rejectedClaims"], [])

    def test_model_name_does_not_change_a_current_cache(self):
        a = evaluate(_payload(model="Galaxy S23"))
        b = evaluate(_payload(model="SM-S911"))
        self.assertEqual(a, b)
        self.assertEqual(a["decision"], "cache_current")

    def test_invalid_payload_raises(self):
        valid = _payload()
        cases = [
            None,
            {},
            {**valid, "variant": "unchanged", "current": {**valid["current"], "codecIdentity": "other"}},
            {**valid, "modelName": ""},
            {**valid, "variant": "firmware"},
            {**valid, "cached": {**valid["cached"], "previouslySuccessful": 1}},
            {k: v for k, v in valid.items() if k != "modelName"},
        ]
        for payload in cases:
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    evaluate(payload)


if __name__ == "__main__":
    unittest.main()
