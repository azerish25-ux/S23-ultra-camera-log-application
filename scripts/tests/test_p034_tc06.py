"""TC-P034-06 calibration identity mismatch."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p034_tc06", Path(__file__).resolve().parents[1] / "gates" / "p034_tc06.py"
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
        "sourceFirmware": "fw-old",
        "sourceCrop": "full",
        "sourceRoute": "rear",
        "sourceCfa": "RGGB",
        "profileFirmware": "fw-old",
        "profileCrop": "full",
        "profileRoute": "rear",
        "profileCfa": "RGGB",
        "uncheckedCurrentDevice": False,
        "provisional": False,
    }
    base.update(overrides)
    return base


class TcP03406(unittest.TestCase):
    def assert_contract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P034-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("source-firmware:fw-old", result["preservedResults"])
        self.assertTrue(result["reasons"])

    def test_module_encodes_case_text(self):
        self.assertIn("firmware, crop, route, or CFA", _MODULE.INTERVENTION)
        self.assertIn("provisional research", _MODULE.EXPECTED)
        self.assertIn("without checking identity", _MODULE.NEGATIVE)

    def test_firmware_mismatch_is_specific(self):
        result = evaluate(payload(profileFirmware="fw-new"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["mismatch:firmware"])
        self.assertIn("source-firmware:fw-old", result["preservedResults"])
        self.assertIn("profile-firmware:fw-new", result["preservedResults"])

    def test_crop_mismatch_is_specific(self):
        result = evaluate(payload(profileCrop="binned"))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["mismatch:crop"])
        self.assertIn("source-crop:full", result["preservedResults"])

    def test_route_mismatch_is_specific(self):
        result = evaluate(payload(profileRoute="front"))
        self.assertEqual(result["rejectedClaims"], ["mismatch:route"])
        self.assertIn("source-route:rear", result["preservedResults"])
        self.assertEqual(result["decision"], "rejected")

    def test_cfa_mismatch_is_specific(self):
        result = evaluate(payload(profileCfa="BGGR"))
        self.assertEqual(result["rejectedClaims"], ["mismatch:cfa"])
        self.assertIn("source-cfa:RGGB", result["preservedResults"])
        self.assertIn("profile-cfa:BGGR", result["preservedResults"])
        self.assertNotEqual(result["decision"], "identity_checked")

    def test_provisional_path_does_not_change_provenance(self):
        result = evaluate(payload(profileFirmware="fw-new", provisional=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "provisional")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("source-firmware:fw-old", result["preservedResults"])
        self.assertNotIn("source-firmware:fw-new", result["preservedResults"])
        self.assertEqual(result["openQuestions"], ["provisional:firmware"])

    def test_negative_unchecked_current_device_fails(self):
        result = evaluate(payload(uncheckedCurrentDevice=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "identity_checked"})
        self.assertEqual(result["rejectedClaims"], ["unchecked-current-device"])
        self.assertIn("source-firmware:fw-old", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_matching_identity_is_not_qualification(self):
        result = evaluate(payload())
        self.assertEqual(result["decision"], "identity_checked")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("physical calibration unverified", result["openQuestions"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate(payload(sourceCfa="YYYY"))


if __name__ == "__main__":
    unittest.main()
