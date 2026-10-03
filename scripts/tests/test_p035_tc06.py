"""TC-P035-06 calibration identity mismatch."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p035_tc06", Path(__file__).resolve().parents[1] / "gates" / "p035_tc06.py"
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
        "field": "firmware",
        "sourceValue": "fw-1",
        "profileValue": "fw-2",
        "path": "check",
        "provenance": "snap:fw-1",
    }
    base.update(overrides)
    return base


class TcP03506(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P035-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_repeat_firmware_mismatch(self):
        result = evaluate(payload(field="firmware"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["mismatch-firmware"])
        self.assertIn("provenance:snap:fw-1", result["preservedResults"])
        self.assertIn("source:firmware=fw-1", result["preservedResults"])
        self.assertIn("profile:firmware=fw-2", result["preservedResults"])

    def test_repeat_crop_mismatch(self):
        result = evaluate(payload(field="crop", sourceValue="1,1,2,2", profileValue="0,0,2,2"))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["mismatch-crop"])
        self.assertIn("provenance:snap:fw-1", result["preservedResults"])

    def test_repeat_route_and_cfa(self):
        route = evaluate(payload(field="route", sourceValue="raw_sensor", profileValue="raw10"))
        cfa = evaluate(payload(field="cfa", sourceValue="RGGB", profileValue="BGGR"))
        self.assertEqual(route["rejectedClaims"], ["mismatch-route"])
        self.assertEqual(cfa["rejectedClaims"], ["mismatch-cfa"])
        self.assertIn("source:cfa=RGGB", cfa["preservedResults"])
        self.assertIn("profile:cfa=BGGR", cfa["preservedResults"])
        self.assertNotIn(cfa["decision"], {"qualified", "allowed"})

    def test_provisional_path_does_not_change_provenance(self):
        result = evaluate(payload(path="provisional"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "provisional")
        self.assertIn("mismatch-firmware", result["rejectedClaims"])
        self.assertIn("provenance:snap:fw-1", result["preservedResults"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_negative_current_device_metadata_fails(self):
        result = evaluate(payload(path="current_device"))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(
            result["rejectedClaims"],
            ["current-device-metadata", "mismatch-firmware"],
        )
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("provenance:snap:fw-1", result["preservedResults"])
        self.assertNotIn("provenance:current", result["preservedResults"])

    def test_matching_identity_is_not_qualification(self):
        result = evaluate(
            payload(field="none", sourceValue="fw-1", profileValue="fw-1", path="check")
        )
        self.assertEqual(result["decision"], "identity_checked")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("provenance:snap:fw-1", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "field": "iso"},
            {**valid, "field": "none"},
            {**valid, "path": "provisional", "field": "none", "sourceValue": "a", "profileValue": "a"},
            {**valid, "provenance": ""},
            {key: value for key, value in valid.items() if key != "path"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
