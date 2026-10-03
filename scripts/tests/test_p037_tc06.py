"""TC-P037-06 calibration identity mismatch."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p037_tc06", Path(__file__).resolve().parents[1] / "gates" / "p037_tc06.py"
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
        "sourceFirmware": "fw1",
        "sourceCrop": "full",
        "sourceRoute": "raw",
        "sourceCfa": "RGGB",
        "profileFirmware": "fw1",
        "profileCrop": "full",
        "profileRoute": "raw",
        "profileCfa": "RGGB",
        "mismatchField": "none",
        "useCurrentDevice": False,
        "provisional": False,
    }
    base.update(overrides)
    return base


class TcP03706(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P037-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_matching_identity_is_checked_not_qualified(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "identity_checked")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("sourceFirmware:fw1", result["preservedResults"])

    def test_firmware_mismatch_is_specific(self):
        result = evaluate(payload(profileFirmware="fw2", mismatchField="firmware"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["identity-mismatch:firmware"])
        self.assertIn("sourceFirmware:fw1", result["preservedResults"])
        self.assertNotIn("sourceFirmware:fw2", result["preservedResults"])

    def test_crop_mismatch_is_specific(self):
        result = evaluate(payload(profileCrop="center", mismatchField="crop"))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["identity-mismatch:crop"])
        self.assertIn("sourceCrop:full", result["preservedResults"])

    def test_route_and_cfa_mismatches_name_the_field(self):
        route = evaluate(payload(profileRoute="yuv", mismatchField="route"))
        cfa = evaluate(payload(profileCfa="BGGR", mismatchField="cfa"))
        self.assertEqual(route["rejectedClaims"], ["identity-mismatch:route"])
        self.assertEqual(cfa["rejectedClaims"], ["identity-mismatch:cfa"])
        self.assertIn("sourceRoute:raw", route["preservedResults"])
        self.assertIn("sourceCfa:RGGB", cfa["preservedResults"])

    def test_provisional_path_does_not_change_provenance(self):
        result = evaluate(
            payload(profileFirmware="fw9", mismatchField="firmware", provisional=True)
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "provisional_research")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("sourceFirmware:fw1", result["preservedResults"])
        self.assertNotIn("sourceFirmware:fw9", result["preservedResults"])
        self.assertTrue(any("provenance unchanged" in item for item in result["reasons"]))

    def test_current_device_metadata_without_a_check_fails(self):
        result = evaluate(payload(useCurrentDevice=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("unchecked-current-device-metadata", result["rejectedClaims"])
        self.assertIn("sourceFirmware:fw1", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "mismatchField": "firmware"},
            {**valid, "provisional": True},
            {**valid, "useCurrentDevice": "yes"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
