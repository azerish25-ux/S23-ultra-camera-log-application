"""TC-P009-04 firmware cache staleness."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p009_tc04", Path(__file__).resolve().parents[1] / "gates" / "p009_tc04.py"
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
        "logicalId": "rear",
        "physicalId": "tele-sensor",
        "buildFingerprint": "samsung/dm3q/build-a",
        "codecIdentity": "c2.exynos.hevc.encoder/1",
        "probeProtocol": "p009-probe-3",
        "qualified": True,
    }
    base.update(overrides)
    return base


def current(**overrides):
    base = {
        "buildFingerprint": "samsung/dm3q/build-a",
        "codecIdentity": "c2.exynos.hevc.encoder/1",
        "probeProtocol": "p009-probe-3",
    }
    base.update(overrides)
    return base


def payload(**overrides):
    base = {
        "cached": cached(),
        "current": current(),
        "variant": "unchanged",
    }
    base.update(overrides)
    return base


class TcP00904(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P009-04")
        self.assertIn(result["decision"], {"requalify", "qualified", "unqualified"})
        self.assertNotEqual(result["decision"], "allowed")
        self.assertIsInstance(result["reasons"], list)
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) for item in result[key]))
        self.assertEqual(result["openQuestions"], ["focal unknown"])

    def assertHistoricalOwner(self, result):
        self.assertEqual(result["decision"], "requalify")
        self.assertNotEqual(result["decision"], "qualified")
        self.assertIn("cache-hit", result["rejectedClaims"])
        self.assertEqual(result["rejectedClaims"], ["cache-hit"])
        self.assertIn("historical:rear", result["preservedResults"])
        self.assertEqual(result["preservedResults"], ["historical:rear"])
        self.assertNotIn("tele-sensor", result["preservedResults"])
        self.assertNotIn("historical:tele-sensor", result["preservedResults"])
        self.assertIn("tele-sensor addressed via rear", result["reasons"])
        self.assertNotIn("mm", json.dumps(result).lower())
        self.assertNotIn("lens", json.dumps(result).lower())

    def test_build_change_requalifies_even_when_cache_was_qualified(self):
        result = evaluate(
            payload(
                cached=cached(qualified=True),
                current=current(buildFingerprint="samsung/dm3q/build-b"),
                variant="build_changed",
            )
        )
        self.assertContract(result)
        self.assertHistoricalOwner(result)
        self.assertIn("buildFingerprint differs from the cached probe", result["reasons"])
        self.assertTrue(any("historical" in item for item in result["reasons"]))

    def test_changed_probe_protocol_requalifies(self):
        result = evaluate(
            payload(
                cached=cached(qualified=True),
                current=current(probeProtocol="p009-probe-4"),
                variant="protocol_changed",
            )
        )
        self.assertContract(result)
        self.assertHistoricalOwner(result)
        self.assertIn("probeProtocol differs from the cached probe", result["reasons"])
        self.assertNotIn("codecIdentity differs from the cached probe", result["reasons"])
        self.assertNotIn("buildFingerprint differs from the cached probe", result["reasons"])

    def test_unchanged_hardware_with_updated_codec_software_requalifies(self):
        result = evaluate(
            payload(
                cached=cached(qualified=True, buildFingerprint="samsung/dm3q/build-a"),
                current=current(
                    buildFingerprint="samsung/dm3q/build-a",
                    codecIdentity="c2.exynos.hevc.encoder/2",
                ),
                variant="codec_changed",
            )
        )
        self.assertContract(result)
        self.assertHistoricalOwner(result)
        self.assertIn("codecIdentity differs from the cached probe", result["reasons"])
        self.assertNotIn("buildFingerprint differs from the cached probe", result["reasons"])

    def test_every_changed_variant_rejects_the_cache_hit(self):
        changes = {
            "build_changed": {"buildFingerprint": "samsung/dm3q/build-b"},
            "codec_changed": {"codecIdentity": "c2.exynos.hevc.encoder/9"},
            "protocol_changed": {"probeProtocol": "p009-probe-9"},
        }
        for variant, fields in changes.items():
            result = evaluate(
                payload(
                    cached=cached(qualified=True),
                    current=current(**fields),
                    variant=variant,
                )
            )
            with self.subTest(variant=variant):
                self.assertContract(result)
                self.assertHistoricalOwner(result)

    def test_stale_negative_cache_is_requalify_not_unqualified(self):
        result = evaluate(
            payload(
                cached=cached(qualified=False),
                current=current(codecIdentity="c2.exynos.hevc.encoder/2"),
                variant="codec_changed",
            )
        )
        self.assertEqual(result["decision"], "requalify")
        self.assertNotEqual(result["decision"], "unqualified")
        self.assertNotEqual(result["decision"], "qualified")
        self.assertEqual(result["rejectedClaims"], ["cache-hit"])
        self.assertEqual(result["preservedResults"], ["historical:rear"])

    def test_matching_qualified_cache_stays_qualified(self):
        result = evaluate(payload(variant="unchanged"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "qualified")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"], ["rear"])
        self.assertNotIn("historical:rear", result["preservedResults"])
        self.assertNotIn("cache-hit", result["rejectedClaims"])
        self.assertNotIn("tele-sensor", result["preservedResults"])
        self.assertIn("tele-sensor addressed via rear", result["reasons"])
        self.assertNotIn("mm", json.dumps(result).lower())

    def test_matching_unqualified_cache_stays_unqualified(self):
        result = evaluate(
            payload(cached=cached(qualified=False), variant="unchanged")
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "unqualified")
        self.assertNotEqual(result["decision"], "qualified")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"], [])
        self.assertIn("tele-sensor addressed via rear", result["reasons"])

    def test_model_name_does_not_bypass_a_changed_environment(self):
        changed = payload(
            cached=cached(qualified=True),
            current=current(buildFingerprint="samsung/dm3q/build-b"),
            variant="build_changed",
        )
        named = {
            "modelName": "SM-S918U",
            "cached": cached(qualified=True, modelName="Galaxy S23 Ultra"),
            "current": current(
                buildFingerprint="samsung/dm3q/build-b",
                modelName="SM-S918U",
            ),
            "variant": "build_changed",
        }
        before = json.dumps(named, sort_keys=True)
        plain = evaluate(changed)
        branded = evaluate(named)
        self.assertEqual(before, json.dumps(named, sort_keys=True))
        self.assertEqual(plain["decision"], branded["decision"])
        self.assertEqual(branded["decision"], "requalify")
        self.assertNotEqual(branded["decision"], "qualified")
        self.assertEqual(plain["rejectedClaims"], branded["rejectedClaims"])
        self.assertEqual(plain["preservedResults"], branded["preservedResults"])
        self.assertNotIn("SM-S918U", json.dumps(branded))
        self.assertNotIn("Galaxy S23 Ultra", json.dumps(branded))

    def test_model_name_does_not_force_requalification_when_identities_match(self):
        named = {
            "modelName": "other-marketing-name",
            "cached": cached(qualified=True, modelName="Galaxy S23 Ultra"),
            "current": current(modelName="SM-S918B"),
            "variant": "unchanged",
        }
        result = evaluate(named)
        self.assertEqual(result["decision"], "qualified")
        self.assertEqual(result["preservedResults"], ["rear"])
        self.assertEqual(result["rejectedClaims"], [])
        self.assertNotIn("other-marketing-name", json.dumps(result))
        unqualified = evaluate(
            {
                "modelName": "SM-S918U",
                "cached": cached(qualified=False),
                "current": current(),
                "variant": "unchanged",
            }
        )
        self.assertEqual(unqualified["decision"], "unqualified")

    def test_variant_label_cannot_hide_a_codec_or_protocol_change(self):
        codec = evaluate(
            payload(
                current=current(codecIdentity="c2.exynos.hevc.encoder/2"),
                variant="unchanged",
            )
        )
        protocol = evaluate(
            payload(
                current=current(probeProtocol="p009-probe-4"),
                variant="build_changed",
            )
        )
        self.assertHistoricalOwner(codec)
        self.assertHistoricalOwner(protocol)
        matched = evaluate(
            payload(
                cached=cached(qualified=True),
                current=current(),
                variant="codec_changed",
            )
        )
        self.assertEqual(matched["decision"], "qualified")

    def test_multiple_identity_changes_are_one_cache_hit(self):
        result = evaluate(
            payload(
                current=current(
                    buildFingerprint="samsung/dm3q/build-b",
                    codecIdentity="c2.exynos.hevc.encoder/2",
                    probeProtocol="p009-probe-4",
                ),
                variant="build_changed",
            )
        )
        self.assertHistoricalOwner(result)
        self.assertEqual(
            result["reasons"][:3],
            [
                "buildFingerprint differs from the cached probe",
                "codecIdentity differs from the cached probe",
                "probeProtocol differs from the cached probe",
            ],
        )

    def test_public_physical_id_needs_no_owner_bridge(self):
        result = evaluate(
            payload(
                cached=cached(physicalId="rear", qualified=True),
                variant="unchanged",
            )
        )
        self.assertEqual(result["decision"], "qualified")
        self.assertEqual(result["preservedResults"], ["rear"])
        self.assertFalse(any("addressed via" in item for item in result["reasons"]))

    def test_logical_only_cache_preserves_the_logical_owner(self):
        result = evaluate(
            payload(
                cached=cached(physicalId=None, qualified=True),
                current=current(buildFingerprint="samsung/dm3q/build-c"),
                variant="build_changed",
            )
        )
        self.assertEqual(result["decision"], "requalify")
        self.assertEqual(result["preservedResults"], ["historical:rear"])
        self.assertFalse(any("addressed via" in item for item in result["reasons"]))

    def test_invalid_payload_raises(self):
        valid_cached = cached()
        valid_current = current()
        cases = [
            None,
            [],
            {},
            {"cached": valid_cached, "current": valid_current},
            {"current": valid_current, "variant": "unchanged"},
            {"cached": valid_cached, "variant": "unchanged"},
            {
                "cached": valid_cached,
                "current": valid_current,
                "variant": "unchanged",
                "extra": True,
            },
            {
                "cached": valid_cached,
                "current": valid_current,
                "variant": "stale",
            },
            {
                "cached": valid_cached,
                "current": valid_current,
                "variant": "UNCHANGED",
            },
            {"cached": [], "current": valid_current, "variant": "unchanged"},
            {"cached": valid_cached, "current": [], "variant": "codec_changed"},
            {
                "cached": {**valid_cached, "lens": "invented"},
                "current": valid_current,
                "variant": "unchanged",
            },
            {
                "cached": {key: value for key, value in valid_cached.items() if key != "qualified"},
                "current": valid_current,
                "variant": "unchanged",
            },
            {
                "cached": {**valid_cached, "logicalId": ""},
                "current": valid_current,
                "variant": "unchanged",
            },
            {
                "cached": {**valid_cached, "physicalId": ""},
                "current": valid_current,
                "variant": "build_changed",
            },
            {
                "cached": {**valid_cached, "qualified": "true"},
                "current": valid_current,
                "variant": "unchanged",
            },
            {
                "cached": {**valid_cached, "qualified": 1},
                "current": valid_current,
                "variant": "unchanged",
            },
            {
                "cached": {**valid_cached, "buildFingerprint": ""},
                "current": valid_current,
                "variant": "build_changed",
            },
            {
                "cached": valid_cached,
                "current": {**valid_current, "codecIdentity": None},
                "variant": "codec_changed",
            },
            {
                "cached": valid_cached,
                "current": {key: value for key, value in valid_current.items() if key != "probeProtocol"},
                "variant": "protocol_changed",
            },
            {
                "cached": valid_cached,
                "current": {**valid_current, "marketingName": "Galaxy"},
                "variant": "unchanged",
            },
            {
                "modelName": "SM-S918U",
                "cached": {key: value for key, value in valid_cached.items() if key != "logicalId"},
                "current": valid_current,
                "variant": "unchanged",
            },
        ]
        for case in cases:
            with self.subTest(payload=case):
                with self.assertRaises(ValueError):
                    evaluate(case)


if __name__ == "__main__":
    unittest.main()
