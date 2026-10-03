"""TC-P013-04 a marketing model name does not bypass a changed codec cache."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p013_tc04", Path(__file__).resolve().parents[1] / "gates" / "p013_tc04.py"
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


def cached(**overrides):
    base = {
        "tupleId": "hevc-main10-surface",
        "buildFingerprint": "build-a",
        "codecIdentity": "codec-a",
        "probeProtocol": "protocol-a",
        "previouslySuccessful": True,
    }
    base.update(overrides)
    return base


def current(**overrides):
    base = {
        "buildFingerprint": "build-a",
        "codecIdentity": "codec-a",
        "probeProtocol": "protocol-a",
    }
    base.update(overrides)
    return base


def payload(cached_row, current_row, variant, model="Galaxy S23 Ultra"):
    return {
        "cached": cached_row,
        "current": current_row,
        "modelName": model,
        "variant": variant,
    }


class TcP01304(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P013-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(result["decision"], {"requalify", "current", "unqualified"})
        self.assertTrue(result["reasons"])
        self.assertTrue(result["preservedResults"])

    def test_updated_codec_software_on_same_model_requires_requalify(self):
        result = evaluate(
            payload(
                cached(),
                current(codecIdentity="codec-b"),
                "codec_changed",
                model="Galaxy S23 Ultra",
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "requalify")
        self.assertEqual(result["rejectedClaims"], ["cache-hit", "model-name-bypass"])
        self.assertEqual(result["preservedResults"], ["historical:hevc-main10-surface"])
        self.assertNotIn("hevc-main10-surface", result["preservedResults"])
        self.assertTrue(any("Galaxy S23 Ultra" in item for item in result["reasons"]))
        self.assertTrue(any("codec" in item for item in result["reasons"]))
        self.assertNotIn(result["decision"], {"qualified", "allowed", "current"})

    def test_changed_probe_protocol_is_historical_only(self):
        result = evaluate(
            payload(cached(), current(probeProtocol="protocol-b"), "protocol_changed")
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "requalify")
        self.assertIn("model-name-bypass", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"], ["historical:hevc-main10-surface"])
        self.assertTrue(any("probe-protocol" in item for item in result["reasons"]))

    def test_build_change_does_not_keep_a_successful_cache_hit(self):
        result = evaluate(payload(cached(), current(buildFingerprint="build-b"), "build_changed"))
        self.assertEqual(result["decision"], "requalify")
        self.assertIn("cache-hit", result["rejectedClaims"])
        self.assertIn("historical:hevc-main10-surface", result["preservedResults"])

    def test_unchanged_identity_can_be_current_without_qualification(self):
        result = evaluate(payload(cached(), current(), "unchanged"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "current")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("hevc-main10-surface", result["preservedResults"])
        self.assertIn("historical:hevc-main10-surface", result["preservedResults"])
        self.assertTrue(any("not a new physical qualification" in item for item in result["reasons"]))

    def test_unchanged_unsuccessful_probe_stays_unqualified(self):
        result = evaluate(
            payload(cached(previouslySuccessful=False), current(), "unchanged")
        )
        self.assertEqual(result["decision"], "unqualified")
        self.assertEqual(result["preservedResults"], ["historical:hevc-main10-surface"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "current"})

    def test_invalid_payload_raises(self):
        valid = payload(cached(), current(), "unchanged")
        cases = [
            None,
            {},
            {**valid, "variant": "model_only"},
            {**valid, "modelName": "  "},
            {**valid, "cached": cached(previouslySuccessful=1)},
            {**valid, "current": {"buildFingerprint": "build-a"}},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
