"""TC-P018-03 interruption during transition."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p018_tc03", Path(__file__).resolve().parents[1] / "gates" / "p018_tc03.py"
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
        "boundary": "starting",
        "selectedAudio": True,
        "interruption": "permission",
        "permanentlyStarting": False,
        "silentContractSwitch": False,
        "availableFootage": ["clip-a"],
        "heldResources": ["camera-a", "mic-a"],
    }
    base.update(overrides)
    return base


class TcP01803(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P018-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_module_encodes_the_case_contract(self):
        self.assertIn("halfway through an asynchronous transition", _MODULE.INTERVENTION)
        self.assertIn("available footage retained", _MODULE.EXPECTED)
        self.assertIn("permanently starting", _MODULE.NEGATIVE)
        self.assertIn("selected audio", _MODULE.REPEAT)

    def test_starting_with_audio_reaches_failure_and_keeps_footage(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "terminal")
        self.assertIn("footage:clip-a", result["preservedResults"])
        self.assertIn("state:failure", result["preservedResults"])
        self.assertNotIn("state:starting", result["preservedResults"])
        self.assertIn("released:camera-a", result["preservedResults"])
        self.assertIn("released:mic-a", result["preservedResults"])
        self.assertTrue(any("audio selected" == item for item in result["reasons"]))

    def test_recording_without_audio_stops_on_screen_loss(self):
        result = evaluate(
            payload(
                boundary="recording",
                selectedAudio=False,
                interruption="screen_attachment",
                availableFootage=["clip-a", "clip-b"],
                heldResources=["display"],
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "terminal")
        self.assertIn("state:stopping", result["preservedResults"])
        self.assertIn("footage:clip-a", result["preservedResults"])
        self.assertIn("footage:clip-b", result["preservedResults"])
        self.assertIn("released:display", result["preservedResults"])
        self.assertTrue(any("audio not selected" == item for item in result["reasons"]))
        self.assertNotEqual(result["decision"], "starting")

    def test_preview_screen_loss_recovers_without_dropping_footage(self):
        result = evaluate(
            payload(
                boundary="preview",
                selectedAudio=False,
                interruption="screen_attachment",
                availableFootage=[],
                heldResources=["display"],
            )
        )
        self.assertEqual(result["decision"], "recovered")
        self.assertIn("state:preview", result["preservedResults"])
        self.assertIn("released:display", result["preservedResults"])

    def test_permanently_starting_and_silent_contract_switch_are_rejected(self):
        result = evaluate(payload(permanentlyStarting=True, silentContractSwitch=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(
            result["rejectedClaims"],
            ["permanently-starting", "silent-contract-switch"],
        )
        self.assertIn("footage:clip-a", result["preservedResults"])
        self.assertNotIn("state:starting", result["preservedResults"])
        self.assertIn("released:camera-a", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "boundary": "idle"},
            {**valid, "interruption": "thermal"},
            {**valid, "selectedAudio": "yes"},
            {**valid, "availableFootage": ["clip-a", "clip-a"]},
            {**valid, "heldResources": [""]},
            {k: v for k, v in valid.items() if k != "boundary"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
