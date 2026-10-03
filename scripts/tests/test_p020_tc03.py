"""TC-P020-03 host checks. Not a physical S23 probe."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p020_tc03", Path(__file__).resolve().parents[1] / "gates" / "p020_tc03.py"
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
_INVENTORY = _MODULE.WB_INVENTORY


def _contract(test, result):
    test.assertEqual(tuple(result), _KEYS)
    test.assertEqual(result["caseId"], "TC-P020-03")
    test.assertNotIn(result["decision"], {"qualified", "allowed"})
    test.assertIsInstance(result["reasons"], list)
    test.assertTrue(result["reasons"])
    test.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
    for key in ("rejectedClaims", "preservedResults", "openQuestions"):
        test.assertIsInstance(result[key], list)
        test.assertTrue(all(isinstance(item, str) for item in result[key]))


def _inventory(test, result):
    for item in _INVENTORY:
        test.assertIn(item, result["preservedResults"])


def payload(**overrides):
    base = {
        "boundary": "permission",
        "audioSelected": False,
        "permanentlyStarting": False,
        "silentContractSwitch": False,
        "footageIds": ["take-a"],
        "releasedResources": ["camera-session"],
    }
    base.update(overrides)
    return base


class TcP02003(unittest.TestCase):
    def test_module_encodes_the_case_text(self):
        self.assertIn("asynchronous transition", _MODULE.INTERVENTION)
        self.assertIn("footage retained", _MODULE.EXPECTED)
        self.assertIn("capture contract", _MODULE.NEGATIVE)
        self.assertEqual(_MODULE.REPEATS, ("permission", "camera_availability", "screen_attachment"))

    def test_permission_without_audio_recovers_and_keeps_footage(self):
        result = evaluate(payload())
        _contract(self, result)
        self.assertEqual(result["decision"], "recovered")
        self.assertIn("footage:take-a", result["preservedResults"])
        self.assertIn("audio:absent", result["preservedResults"])
        _inventory(self, result)
        self.assertTrue(any("permission" in item and "false" in item for item in result["reasons"]))

    def test_camera_availability_with_audio_recovers(self):
        result = evaluate(payload(boundary="camera_availability", audioSelected=True, footageIds=["take-b"]))
        _contract(self, result)
        self.assertEqual(result["decision"], "recovered")
        self.assertIn("audio:selected", result["preservedResults"])
        self.assertIn("footage:take-b", result["preservedResults"])
        _inventory(self, result)
        self.assertTrue(any("camera_availability" in item for item in result["reasons"]))

    def test_permanently_starting_on_screen_attachment_is_rejected(self):
        result = evaluate(payload(boundary="screen_attachment", permanentlyStarting=True))
        _contract(self, result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "recovered"})
        self.assertIn("permanently-starting", result["rejectedClaims"])
        self.assertIn("footage:take-a", result["preservedResults"])
        _inventory(self, result)

    def test_silent_contract_switch_is_rejected(self):
        result = evaluate(payload(boundary="permission", audioSelected=True, silentContractSwitch=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("silent-contract-switch", result["rejectedClaims"])
        _inventory(self, result)
        self.assertIn("creative.slider:warm", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [None, {**valid, "boundary": "iso"}, {**valid, "audioSelected": "yes"}, {**valid, "extra": True}]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
