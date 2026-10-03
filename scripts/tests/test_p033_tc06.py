"""TC-P033-06 calibration identity mismatch."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p033_tc06", Path(__file__).resolve().parents[1] / "gates" / "p033_tc06.py"
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
_FORBIDDEN = {"qualified", "allowed"}


def payload(**overrides):
    base = {
        "sourceFirmware": "fw-a",
        "sourceCrop": "0,0,64,48",
        "sourceRoute": "logical-0/RAW_SENSOR",
        "sourceCfa": "RGGB",
        "profileFirmware": "fw-a",
        "profileCrop": "0,0,64,48",
        "profileRoute": "logical-0/RAW_SENSOR",
        "profileCfa": "RGGB",
        "provisional": False,
        "useCurrentDeviceMetadata": False,
        "identityChecked": True,
        "provenanceChanged": False,
        "evidenceId": "snap-1",
    }
    base.update(overrides)
    return base


class TcP03306(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P033-06")
        self.assertNotIn(result["decision"], _FORBIDDEN)
        self.assertTrue(result["reasons"])
        self.assertIn("evidence:snap-1", result["preservedResults"])

    def test_repeat_one_identity_field_at_a_time(self):
        variants = (
            ("firmware", {"profileFirmware": "fw-b"}, "source-firmware:fw-a", "profile-firmware:fw-b"),
            ("crop", {"profileCrop": "2,2,60,44"}, "source-crop:0,0,64,48", "profile-crop:2,2,60,44"),
            ("route", {"profileRoute": "logical-1/RAW_SENSOR"}, "source-route:logical-0/RAW_SENSOR", "profile-route:logical-1/RAW_SENSOR"),
            ("cfa", {"profileCfa": "BGGR"}, "source-cfa:RGGB", "profile-cfa:BGGR"),
        )
        for field, overrides, source_token, profile_token in variants:
            result = evaluate(payload(**overrides))
            self.assertContract(result)
            self.assertEqual(result["decision"], "rejected")
            self.assertEqual(result["rejectedClaims"], ["mismatch-" + field])
            self.assertNotIn(result["decision"], _FORBIDDEN | {"provisional_research", "identity_checked"})
            self.assertIn(source_token, result["preservedResults"])
            self.assertIn(profile_token, result["preservedResults"])
            self.assertIn("provenance:unchanged", result["preservedResults"])
            self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_provisional_path_does_not_change_provenance(self):
        result = evaluate(payload(profileFirmware="fw-b", provisional=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "provisional_research")
        self.assertNotIn(result["decision"], _FORBIDDEN)
        self.assertEqual(result["rejectedClaims"], ["mismatch-firmware"])
        self.assertIn("provenance:unchanged", result["preservedResults"])
        self.assertIn("evidence:snap-1", result["preservedResults"])
        self.assertIn("source-firmware:fw-a", result["preservedResults"])
        self.assertTrue(any("not qualification" in item for item in result["reasons"]))

    def test_negative_unchecked_current_metadata_fails(self):
        result = evaluate(
            payload(
                useCurrentDeviceMetadata=True,
                identityChecked=False,
                profileFirmware="fw-current",
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], _FORBIDDEN | {"identity_checked", "provisional_research"})
        self.assertIn("unchecked-current-metadata", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("source-firmware:fw-a", result["preservedResults"])
        self.assertIn("profile-firmware:fw-current", result["preservedResults"])
        self.assertIn("evidence:snap-1", result["preservedResults"])

    def test_matching_identity_is_not_qualified(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "identity_checked")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertNotIn(result["decision"], _FORBIDDEN)
        self.assertIn("provenance:unchanged", result["preservedResults"])
        self.assertTrue(any("not a measured calibration" in item for item in result["reasons"]))

    def test_provenance_change_is_rejected(self):
        result = evaluate(payload(provenanceChanged=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("provenance-changed", result["rejectedClaims"])
        self.assertIn("provenance:changed", result["preservedResults"])
        self.assertIn("evidence:snap-1", result["preservedResults"])
        self.assertNotIn(result["decision"], _FORBIDDEN)

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "sourceCfa": "RGBG"},
            {**valid, "profileCfa": "rggb"},
            {**valid, "identityChecked": "true"},
            {**valid, "sourceFirmware": ""},
            {**valid, "evidenceId": " snap-1"},
            {**valid, "provisional": 1},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
