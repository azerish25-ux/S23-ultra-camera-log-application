"""TC-P015-04 a marketing-name cache hit does not bypass a changed environment."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p015_tc04", Path(__file__).resolve().parents[1] / "gates" / "p015_tc04.py"
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


def record(**overrides):
    base = {
        "tupleId": "logical:0|hevc-main10",
        "reportId": "hist-firmware-a",
        "buildFingerprint": "fp-firmware-a",
        "appProtocolVersion": "capability-probe/1",
        "route": "logical:0",
        "codecIdentity": "c2.exynos.hevc.encoder/1.0",
        "codecCapabilityResponse": "Main10-surface-available",
        "marketingName": "Galaxy S23 Ultra",
        "previouslySuccessful": True,
    }
    base.update(overrides)
    return base


def payload(variant, current_overrides):
    return {"cached": record(), "current": record(**current_overrides), "variant": variant}


class TcP01504(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P015-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_contract_text(self):
        self.assertIn("previously successful cached probe", _MODULE.INTERVENTION)
        self.assertIn("historical evidence", _MODULE.EXPECTED)
        self.assertIn("marketing-model-name", _MODULE.NEGATIVE)
        self.assertIn("app probe protocol", _MODULE.REPEAT)
        self.assertIn("codec software", _MODULE.REPEAT)

    def test_build_change_keeps_the_old_report_historical(self):
        result = evaluate(payload("build_changed", {"buildFingerprint": "fp-firmware-b"}))
        self.assertContract(result)
        self.assertEqual(result["decision"], "requalify")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "cache_valid"})
        self.assertEqual(result["preservedResults"], ["historical:hist-firmware-a"])
        self.assertIn("marketing-name-cache-hit", result["rejectedClaims"])
        self.assertEqual(result["openQuestions"], ["requalification pending"])
        self.assertTrue(any("does not bypass" in item for item in result["reasons"]))

    def test_changed_app_probe_protocol_requires_requalification(self):
        result = evaluate(payload("protocol_changed", {"appProtocolVersion": "capability-probe/2"}))
        self.assertEqual(result["decision"], "requalify")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("historical:hist-firmware-a", result["preservedResults"])
        self.assertTrue(any("protocol_changed" in item for item in result["reasons"]))
        self.assertNotIn("logical:0|hevc-main10", result["preservedResults"])

    def test_updated_codec_software_on_unchanged_hardware(self):
        result = evaluate(
            payload("codec_software", {"codecIdentity": "c2.exynos.hevc.encoder/2.0"})
        )
        self.assertEqual(result["decision"], "requalify")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "cache_valid"})
        self.assertEqual(result["preservedResults"], ["historical:hist-firmware-a"])
        self.assertIn("marketing-name-cache-hit", result["rejectedClaims"])
        self.assertTrue(any("codec_software" in item for item in result["reasons"]))

    def test_unchanged_identity_is_cache_valid_not_qualified(self):
        result = evaluate(payload("unchanged", {}))
        self.assertEqual(result["decision"], "cache_valid")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(
            result["preservedResults"],
            ["historical:hist-firmware-a", "logical:0|hevc-main10"],
        )
        self.assertTrue(any("not physical S23 qualification" in item for item in result["reasons"]))

    def test_invalid_payload_raises(self):
        valid = payload("unchanged", {})
        drifted = payload("unchanged", {"buildFingerprint": "other"})
        cases = [
            None,
            {},
            {**valid, "variant": "marketing"},
            drifted,
            {"cached": record(previouslySuccessful=False), "current": record(), "variant": "unchanged"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
