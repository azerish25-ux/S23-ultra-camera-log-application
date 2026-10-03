"""TC-P039-06 calibration identity mismatch."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p039_tc06", Path(__file__).resolve().parents[1] / "gates" / "p039_tc06.py"
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
        "sourceCrop": "crop-a",
        "sourceRoute": "route-0",
        "sourceCfa": "RGGB",
        "profileFirmware": "fw-1",
        "profileCrop": "crop-a",
        "profileRoute": "route-0",
        "profileCfa": "RGGB",
        "mismatchField": "none",
        "useCurrentDevice": False,
        "provisional": False,
    }
    base.update(overrides)
    return base


class TcP03906(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P039-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def assert_source(self, result):
        self.assertIn("sourceFirmware:fw-1", result["preservedResults"])
        self.assertIn("sourceCrop:crop-a", result["preservedResults"])
        self.assertIn("sourceRoute:route-0", result["preservedResults"])
        self.assertIn("sourceCfa:RGGB", result["preservedResults"])

    def test_matching_identity_is_checked_not_qualified(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "identity_checked")
        self.assertEqual(result["rejectedClaims"], [])
        self.assert_source(result)

    def test_firmware_mismatch_is_rejected(self):
        result = evaluate(payload(profileFirmware="fw-2", mismatchField="firmware"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("identity-mismatch:firmware", result["rejectedClaims"])
        self.assert_source(result)
        self.assertIn("firmware mismatch", result["openQuestions"])

    def test_crop_mismatch_is_rejected(self):
        result = evaluate(payload(profileCrop="crop-b", mismatchField="crop"))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("identity-mismatch:crop", result["rejectedClaims"])
        self.assert_source(result)

    def test_current_device_metadata_negative_is_rejected(self):
        result = evaluate(payload(useCurrentDevice=True, profileFirmware="fw-2", mismatchField="firmware"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("unchecked-current-device-metadata", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assert_source(result)

    def test_provisional_path_keeps_source_provenance(self):
        result = evaluate(
            payload(profileRoute="route-1", mismatchField="route", provisional=True)
        )
        self.assertEqual(result["decision"], "provisional_research")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assert_source(result)
        self.assertIn("provisional route mismatch", result["openQuestions"])


if __name__ == "__main__":
    unittest.main()
