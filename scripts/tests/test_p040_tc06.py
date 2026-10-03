"""TC-P040-06 calibration identity mismatch."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p040_tc06", Path(__file__).resolve().parents[1] / "gates" / "p040_tc06.py"
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
        "sourceFirmware": "fw-1",
        "profileFirmware": "fw-1",
        "sourceCrop": "4000x3000+0+0",
        "profileCrop": "4000x3000+0+0",
        "sourceRoute": "raw",
        "profileRoute": "raw",
        "sourceCfa": "RGGB",
        "profileCfa": "RGGB",
        "path": "reject",
        "provenance": "prov-keep",
    }
    base.update(overrides)
    return base


class TcP04006(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P040-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertEqual(result["preservedResults"][0], "prov-keep")

    def test_intervention_expected_and_negative_are_encoded(self):
        self.assertIn("firmware, crop, route, or CFA", _MODULE.INTERVENTION)
        self.assertIn("provisional research path", _MODULE.EXPECTED)
        self.assertIn("without checking identity", _MODULE.NEGATIVE)

    def test_matching_identity_is_checked_and_provenance_stays(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "checked")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("source.firmware:fw-1", result["preservedResults"])
        self.assertIn("profile.cfa:RGGB", result["preservedResults"])

    def test_firmware_mismatch_has_a_specific_reason(self):
        result = evaluate(payload(profileFirmware="fw-2"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["identity-mismatch:firmware"])
        self.assertIn("source.firmware:fw-1", result["preservedResults"])
        self.assertIn("profile.firmware:fw-2", result["preservedResults"])
        self.assertIn("mismatch firmware", result["reasons"])
        self.assertEqual(result["preservedResults"][0], "prov-keep")

    def test_crop_mismatch_has_a_specific_reason(self):
        result = evaluate(payload(profileCrop="1920x1080+0+0"))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["identity-mismatch:crop"])
        self.assertIn("profile.crop:1920x1080+0+0", result["preservedResults"])
        self.assertIn("mismatch crop", result["reasons"])
        self.assertEqual(result["preservedResults"][0], "prov-keep")

    def test_route_mismatch_has_a_specific_reason(self):
        result = evaluate(payload(profileRoute="yuv"))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["identity-mismatch:route"])
        self.assertIn("source.route:raw", result["preservedResults"])
        self.assertIn("mismatch route", result["reasons"])

    def test_cfa_mismatch_has_a_specific_reason(self):
        result = evaluate(payload(profileCfa="BGGR"))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["identity-mismatch:cfa"])
        self.assertIn("source.cfa:RGGB", result["preservedResults"])
        self.assertIn("profile.cfa:BGGR", result["preservedResults"])
        self.assertIn("mismatch cfa", result["reasons"])

    def test_provisional_path_does_not_change_provenance(self):
        result = evaluate(payload(profileFirmware="fw-9", path="provisional"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "provisional")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], ["identity-mismatch:firmware"])
        self.assertEqual(result["preservedResults"][0], "prov-keep")
        self.assertIn("provisional research path is not production development", result["openQuestions"])
        self.assertIn("explicit provisional research path", result["reasons"])

    def test_negative_unchecked_current_metadata_fails(self):
        result = evaluate(payload(path="unchecked", profileCfa="GRBG"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "checked"})
        self.assertEqual(
            result["rejectedClaims"],
            ["unchecked-current-device-metadata", "identity-mismatch:cfa"],
        )
        self.assertEqual(result["preservedResults"][0], "prov-keep")
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("identity was not checked", result["openQuestions"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "path"},
            {**valid, "extra": True},
            {**valid, "sourceCfa": "RGB"},
            {**valid, "path": "allow"},
            {**valid, "provenance": ""},
            {**valid, "sourceCrop": "  "},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
