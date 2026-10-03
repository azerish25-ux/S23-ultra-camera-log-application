"""TC-P038-06 one identity field at a time, plus the current-metadata negative."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p038_tc06", Path(__file__).resolve().parents[1] / "gates" / "p038_tc06.py"
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
_PROVENANCE = "capture-snapshot:take-fw1"


def payload(**overrides):
    base = {
        "sourceFirmware": "fw-1.0.0",
        "sourceCrop": "4000x3000+8+8",
        "sourceRoute": "logical0/physical-main/RAW_SENSOR",
        "sourceCfa": "RGGB",
        "sourceHandset": "handset-a",
        "sourceProvenance": _PROVENANCE,
        "profileFirmware": "fw-1.0.0",
        "profileCrop": "4000x3000+8+8",
        "profileRoute": "logical0/physical-main/RAW_SENSOR",
        "profileCfa": "RGGB",
        "profileHandset": "handset-a",
        "profileOrigin": "capture-snapshot",
        "provisional": False,
        "checkIdentity": True,
    }
    base.update(overrides)
    return base


class TcP03806(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P038-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertEqual(result["preservedResults"][0], f"provenance:{_PROVENANCE}")

    def test_matching_capture_snapshot_keeps_provenance(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "identity_matched")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("source.firmware:fw-1.0.0", result["preservedResults"])

    def test_each_identity_field_has_its_own_rejection(self):
        cases = (
            ("profileFirmware", "fw-2.0.0", "firmware-mismatch"),
            ("profileCrop", "4000x3000+0+0", "crop-mismatch"),
            ("profileRoute", "logical0/physical-ultra/RAW_SENSOR", "route-mismatch"),
            ("profileCfa", "BGGR", "cfa-mismatch"),
        )
        for key, value, claim in cases:
            result = evaluate(payload(**{key: value}))
            self.assertEqual(result["decision"], "rejected", claim)
            self.assertEqual(result["rejectedClaims"], [claim])
            self.assertEqual(result["preservedResults"][0], f"provenance:{_PROVENANCE}")
            self.assertNotIn(result["decision"], {"qualified", "allowed", "identity_matched"})

    def test_provisional_path_does_not_change_provenance(self):
        result = evaluate(payload(profileFirmware="fw-2.0.0", provisional=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "provisional")
        self.assertEqual(result["rejectedClaims"], ["firmware-mismatch"])
        self.assertEqual(result["preservedResults"][0], f"provenance:{_PROVENANCE}")
        self.assertTrue(any("does not change provenance" in item for item in result["reasons"]))
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_current_device_metadata_without_an_identity_check_fails(self):
        result = evaluate(
            payload(
                profileOrigin="current-device",
                profileFirmware="fw-2.0.0",
                checkIdentity=False,
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("current-metadata-as-capture-truth", result["rejectedClaims"])
        self.assertIn("firmware-mismatch", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertEqual(result["preservedResults"][0], f"provenance:{_PROVENANCE}")
        self.assertNotIn("fw-2.0.0", result["preservedResults"][0])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate(payload(profileOrigin="live"))
        with self.assertRaises(ValueError):
            evaluate(payload(checkIdentity="yes"))


if __name__ == "__main__":
    unittest.main()
