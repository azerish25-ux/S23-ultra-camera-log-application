"""TC-P022-03 interruptions end in a legal terminal state."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p022_tc03", Path(__file__).resolve().parents[1] / "gates" / "p022_tc03.py"
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
_HASH = "cm-interruption"
_FOOTAGE = ["take-kept"]


def payload(**overrides):
    base = {
        "boundary": "permission",
        "audioSelected": True,
        "permanentlyStarting": False,
        "silentContractSwitch": False,
        "resourcesReleased": True,
        "footage": list(_FOOTAGE),
        "terminalState": "stopped",
        "cleanMasterHash": _HASH,
    }
    base.update(overrides)
    return base


class TcP02203(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P022-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_module_encodes_the_case_text(self):
        self.assertIn("asynchronous transition", _MODULE.INTERVENTION)
        self.assertIn("available footage", _MODULE.EXPECTED)
        self.assertIn("permanently starting", _MODULE.NEGATIVE)

    def test_permission_with_audio_stops_and_keeps_footage(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "terminal")
        self.assertEqual(result["preservedResults"], ["take-kept", _HASH])
        self.assertTrue(any("audio selected" in item for item in result["reasons"]))
        self.assertTrue(any("permission" in item for item in result["reasons"]))
        self.assertEqual(result["rejectedClaims"], [])

    def test_camera_availability_without_audio_can_recover(self):
        result = evaluate(
            payload(
                boundary="camera_availability",
                audioSelected=False,
                terminalState="recovering",
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "recovering")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["preservedResults"], ["take-kept", _HASH])
        self.assertTrue(any("audio not selected" in item for item in result["reasons"]))
        self.assertIn("recovery state is not a finished capture", result["openQuestions"])

    def test_permanently_starting_screen_attachment_is_rejected(self):
        result = evaluate(
            payload(boundary="screen_attachment", permanentlyStarting=True, terminalState="starting")
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "terminal"})
        self.assertIn("permanently-starting", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"], ["take-kept", _HASH])

    def test_silent_contract_switch_keeps_footage(self):
        result = evaluate(
            payload(silentContractSwitch=True, terminalState="switched", audioSelected=False)
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("silent-contract-switch", result["rejectedClaims"])
        self.assertIn("take-kept", result["preservedResults"])
        self.assertIn(_HASH, result["preservedResults"])

    def test_held_resources_fail_even_when_the_label_says_stopped(self):
        result = evaluate(payload(resourcesReleased=False))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("resources-held", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"], ["take-kept", _HASH])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "boundary": "thermal"},
            {**valid, "audioSelected": "yes"},
            {**valid, "terminalState": "running"},
            {**valid, "footage": ["take-kept", "take-kept"]},
            {**valid, "extra": False},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
