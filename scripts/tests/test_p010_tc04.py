"""TC-P010-04 cached probe staleness after identity changes."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p010_tc04", Path(__file__).resolve().parents[1] / "gates" / "p010_tc04.py"
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
_MODEL = "Galaxy S23 Ultra"


def _payload(
    *,
    build="fp-hw-1",
    codec="codec-a",
    protocol="probe-3",
    current_build=None,
    current_codec=None,
    current_protocol=None,
    stream_id="rear-raw",
    qualified=True,
    model=_MODEL,
    variant="unchanged",
):
    return {
        "cached": {
            "streamId": stream_id,
            "buildFingerprint": build,
            "codecIdentity": codec,
            "probeProtocol": protocol,
            "qualified": qualified,
        },
        "current": {
            "buildFingerprint": build if current_build is None else current_build,
            "codecIdentity": codec if current_codec is None else current_codec,
            "probeProtocol": protocol if current_protocol is None else current_protocol,
        },
        "modelName": model,
        "variant": variant,
    }


class TcP01004(unittest.TestCase):
    def assertContract(self, result, decision):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P010-04")
        self.assertEqual(result["decision"], decision)
        self.assertNotEqual(result["decision"], "allowed")
        self.assertIsInstance(result["reasons"], list)
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) for item in result[key]))
        self.assertEqual(result["openQuestions"], [])

    def assertHistorical(self, result, stream_id="rear-raw"):
        self.assertContract(result, "requalify")
        self.assertEqual(result["rejectedClaims"], ["cache-hit"])
        self.assertEqual(result["preservedResults"], [f"historical:{stream_id}"])
        self.assertNotIn(result["decision"], {"qualified", "unqualified", "allowed"})
        self.assertNotIn("qualified", json.dumps(result))
        self.assertNotIn(_MODEL, json.dumps(result))

    def test_changed_probe_protocol_requires_requalify(self):
        payload = _payload(current_protocol="probe-4", variant="protocol_changed", qualified=True)
        self.assertEqual(
            payload["cached"]["buildFingerprint"], payload["current"]["buildFingerprint"]
        )
        self.assertEqual(payload["cached"]["codecIdentity"], payload["current"]["codecIdentity"])
        self.assertNotEqual(payload["cached"]["probeProtocol"], payload["current"]["probeProtocol"])
        result = evaluate(payload)
        self.assertHistorical(result)
        self.assertEqual(
            result["reasons"],
            ["cached probe is historical only after probe-protocol identity change"],
        )

    def test_unchanged_hardware_with_updated_codec_requires_requalify(self):
        payload = _payload(current_codec="codec-b", variant="codec_changed", qualified=True)
        self.assertEqual(
            payload["cached"]["buildFingerprint"], payload["current"]["buildFingerprint"]
        )
        self.assertNotEqual(payload["cached"]["codecIdentity"], payload["current"]["codecIdentity"])
        self.assertEqual(payload["cached"]["probeProtocol"], payload["current"]["probeProtocol"])
        result = evaluate(payload)
        self.assertHistorical(result)
        self.assertEqual(
            result["reasons"],
            ["cached probe is historical only after codec identity change"],
        )
        self.assertNotIn("build", result["reasons"][0])
        self.assertNotIn("probe-protocol", result["reasons"][0])

    def test_changed_build_requires_requalify(self):
        payload = _payload(current_build="fp-hw-2", variant="build_changed", qualified=True)
        result = evaluate(payload)
        self.assertHistorical(result)
        self.assertEqual(
            result["reasons"],
            ["cached probe is historical only after build identity change"],
        )

    def test_all_identity_changes_together_are_historical(self):
        result = evaluate(
            _payload(
                current_build="fp-hw-2",
                current_codec="codec-b",
                current_protocol="probe-4",
                variant="build_changed",
                qualified=True,
                stream_id="tele-raw",
            )
        )
        self.assertHistorical(result, "tele-raw")
        self.assertEqual(
            result["reasons"],
            [
                "cached probe is historical only after build, codec, probe-protocol identity change"
            ],
        )

    def test_stale_unqualified_cache_still_requires_requalify(self):
        result = evaluate(
            _payload(current_protocol="probe-9", variant="protocol_changed", qualified=False)
        )
        self.assertHistorical(result)
        self.assertNotEqual(result["decision"], "unqualified")

    def test_unchanged_qualified_cache_stays_qualified(self):
        result = evaluate(_payload(qualified=True, variant="unchanged"))
        self.assertContract(result, "qualified")
        self.assertEqual(
            result["reasons"],
            ["build, codec, and probe-protocol identities match the qualified cached probe"],
        )
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"], ["rear-raw"])
        self.assertNotIn("historical:", result["preservedResults"][0])
        self.assertNotIn("cache-hit", result["rejectedClaims"])
        self.assertNotIn(_MODEL, json.dumps(result))

    def test_unchanged_unqualified_cache_stays_unqualified(self):
        result = evaluate(_payload(qualified=False, variant="unchanged"))
        self.assertContract(result, "unqualified")
        self.assertEqual(
            result["reasons"],
            ["build, codec, and probe-protocol identities match the unqualified cached probe"],
        )
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"], ["rear-raw"])
        self.assertNotIn("cache-hit", result["rejectedClaims"])
        self.assertNotIn(_MODEL, json.dumps(result))

    def test_marketing_model_name_is_ignored(self):
        qualified_a = evaluate(_payload(model="Galaxy S23 Ultra", qualified=True))
        qualified_b = evaluate(_payload(model="marketing-alias", qualified=True))
        self.assertEqual(qualified_a, qualified_b)
        self.assertEqual(qualified_a["decision"], "qualified")
        stale_a = evaluate(
            _payload(model="Galaxy S23 Ultra", current_codec="codec-b", variant="codec_changed")
        )
        stale_b = evaluate(
            _payload(model="SM-S918B", current_codec="codec-b", variant="codec_changed")
        )
        self.assertEqual(stale_a, stale_b)
        self.assertEqual(stale_a["decision"], "requalify")
        for result, name in (
            (qualified_a, "Galaxy S23 Ultra"),
            (qualified_b, "marketing-alias"),
            (stale_a, "Galaxy S23 Ultra"),
            (stale_b, "SM-S918B"),
        ):
            self.assertNotIn(name, json.dumps(result))

    def test_variant_label_does_not_override_identity(self):
        lied_unchanged = evaluate(
            _payload(current_codec="codec-b", variant="unchanged", qualified=True)
        )
        self.assertHistorical(lied_unchanged)
        lied_changed = evaluate(
            _payload(variant="codec_changed", qualified=True)
        )
        self.assertContract(lied_changed, "qualified")
        self.assertEqual(lied_changed["preservedResults"], ["rear-raw"])
        self.assertNotIn("cache-hit", lied_changed["rejectedClaims"])

    def test_invalid_payload_raises(self):
        valid = _payload()
        cached = valid["cached"]
        current = valid["current"]
        cases = [
            None,
            [],
            {},
            {"cached": cached, "current": current, "modelName": _MODEL},
            {"cached": cached, "current": current, "variant": "unchanged"},
            {**valid, "extra": 1},
            {**valid, "variant": "firmware_changed"},
            {**valid, "variant": "UNCHANGED"},
            {**valid, "modelName": ""},
            {**valid, "modelName": None},
            {**valid, "modelName": 23},
            {**valid, "cached": None},
            {**valid, "current": None},
            {**valid, "cached": {**cached, "lens": "tele"}},
            {**valid, "cached": {key: value for key, value in cached.items() if key != "qualified"}},
            {**valid, "current": {**current, "streamId": "rear-raw"}},
            {**valid, "current": {key: value for key, value in current.items() if key != "codecIdentity"}},
            {**valid, "cached": {**cached, "streamId": ""}},
            {**valid, "cached": {**cached, "buildFingerprint": ""}},
            {**valid, "current": {**current, "probeProtocol": ""}},
            {**valid, "cached": {**cached, "codecIdentity": 1}},
            {**valid, "current": {**current, "buildFingerprint": None}},
            {**valid, "cached": {**cached, "qualified": 1}},
            {**valid, "cached": {**cached, "qualified": "true"}},
        ]
        for payload in cases:
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    evaluate(payload)


if __name__ == "__main__":
    unittest.main()
