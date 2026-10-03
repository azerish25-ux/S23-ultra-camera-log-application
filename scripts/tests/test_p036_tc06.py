"""TC-P036-06 calibration identity mismatch."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p036_tc06", Path(__file__).resolve().parents[1] / "gates" / "p036_tc06.py"
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
_PROVENANCE = "source-prov-7"


def payload(**overrides):
    base = {
        "sourceFirmware": "fw-1",
        "profileFirmware": "fw-1",
        "sourceCrop": "4000x3000",
        "profileCrop": "4000x3000",
        "sourceRoute": "raw-main",
        "profileRoute": "raw-main",
        "sourceCfa": "RGGB",
        "profileCfa": "RGGB",
        "path": "reject",
        "provenance": _PROVENANCE,
    }
    base.update(overrides)
    return base


class TcP03606(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P036-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertEqual(result["preservedResults"][0], _PROVENANCE)

    def test_firmware_mismatch_rejects_without_changing_provenance(self):
        result = evaluate(payload(profileFirmware="fw-2"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["identity-mismatch:firmware"])
        self.assertIn("source.firmware:fw-1", result["preservedResults"])
        self.assertIn("profile.firmware:fw-2", result["preservedResults"])
        self.assertTrue(any("mismatch firmware" in item for item in result["reasons"]))

    def test_crop_mismatch_rejects_with_that_reason(self):
        result = evaluate(payload(profileCrop="1920x1080"))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["identity-mismatch:crop"])
        self.assertEqual(result["preservedResults"][0], _PROVENANCE)

    def test_route_mismatch_rejects_with_that_reason(self):
        result = evaluate(payload(profileRoute="preview"))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["identity-mismatch:route"])
        self.assertIn("profile.route:preview", result["preservedResults"])

    def test_cfa_mismatch_rejects_with_that_reason(self):
        result = evaluate(payload(profileCfa="BGGR"))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["identity-mismatch:cfa"])
        self.assertIn("source.cfa:RGGB", result["preservedResults"])
        self.assertEqual(result["preservedResults"][0], _PROVENANCE)

    def test_provisional_path_keeps_provenance(self):
        result = evaluate(payload(profileFirmware="fw-9", path="provisional"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "provisional")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("identity-mismatch:firmware", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][0], _PROVENANCE)
        self.assertIn(
            "provisional research path is not production development",
            result["openQuestions"],
        )

    def test_negative_unchecked_current_device_fails(self):
        result = evaluate(payload(path="unchecked", profileFirmware="fw-current"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "checked"})
        self.assertIn("unchecked-current-device-metadata", result["rejectedClaims"])
        self.assertIn("identity-mismatch:firmware", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][0], _PROVENANCE)
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_matching_identity_is_checked_not_qualified(self):
        result = evaluate(payload())
        self.assertEqual(result["decision"], "checked")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][0], _PROVENANCE)

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "sourceCfa": "XXXX"},
            {**valid, "path": "trust"},
            {**valid, "provenance": ""},
            {**valid, "sourceFirmware": " fw"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
