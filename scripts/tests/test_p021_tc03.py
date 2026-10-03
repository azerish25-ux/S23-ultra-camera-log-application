"""TC-P021-03 interruption during transition."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p021_tc03", Path(__file__).resolve().parents[1] / "gates" / "p021_tc03.py"
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
        "boundary": "permission",
        "audioSelected": False,
        "permanentlyStarting": False,
        "silentContractSwitch": False,
        "footageIds": ["take-a"],
        "releasedResources": ["camera-session"],
    }
    base.update(overrides)
    return base


class TcP02103(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P021-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        for token in _MODULE.FOCUS_INVENTORY:
            self.assertIn(token, result["preservedResults"])
        self.assertIn("footage:take-a", result["preservedResults"])

    def test_module_encodes_intervention_expected_and_negative(self):
        self.assertIn("halfway through an asynchronous transition", _MODULE.INTERVENTION)
        self.assertIn("available footage retained", _MODULE.EXPECTED)
        self.assertIn("permanently starting", _MODULE.NEGATIVE)
        self.assertEqual(
            _MODULE.REPEATS, ("permission", "camera_availability", "screen_attachment")
        )

    def test_repeat_permission_without_audio_recovers(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "recovered")
        self.assertIn("audio:absent", result["preservedResults"])
        self.assertTrue(any("permission" in item and "audio false" in item for item in result["reasons"]))
        self.assertTrue(any("camera-session" in item for item in result["reasons"]))

    def test_repeat_camera_availability_with_audio_recovers(self):
        result = evaluate(payload(boundary="camera_availability", audioSelected=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "recovered")
        self.assertIn("audio:selected", result["preservedResults"])
        self.assertIn("footage:take-a", result["preservedResults"])
        self.assertTrue(any("camera_availability" in item and "audio true" in item for item in result["reasons"]))

    def test_repeat_screen_attachment_recovers(self):
        result = evaluate(payload(boundary="screen_attachment", audioSelected=True, footageIds=["take-a", "take-b"]))
        self.assertEqual(result["decision"], "recovered")
        self.assertIn("footage:take-b", result["preservedResults"])
        self.assertIn("physical.distance:unknown", result["preservedResults"])

    def test_negative_permanently_starting_keeps_footage(self):
        result = evaluate(payload(permanentlyStarting=True, boundary="permission", audioSelected=False))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "recovered"})
        self.assertIn("permanently-starting", result["rejectedClaims"])
        self.assertIn("footage:take-a", result["preservedResults"])

    def test_negative_silent_contract_switch_keeps_footage(self):
        result = evaluate(
            payload(
                silentContractSwitch=True,
                permanentlyStarting=True,
                boundary="screen_attachment",
                audioSelected=True,
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("silent-contract-switch", result["rejectedClaims"])
        self.assertIn("permanently-starting", result["rejectedClaims"])
        self.assertIn("footage:take-a", result["preservedResults"])
        self.assertIn("virtual.subject:face", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {**valid, "boundary": "audio"},
            {**valid, "audioSelected": "yes"},
            {**valid, "footageIds": ["take-a", "take-a"]},
            {**valid, "note": True},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
