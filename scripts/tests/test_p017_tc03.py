"""TC-P017-03 interruption during transition."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p017_tc03", Path(__file__).resolve().parents[1] / "gates" / "p017_tc03.py"
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
        "interruption": "permission",
        "audioSelected": False,
        "permanentStarting": False,
        "silentContractSwitch": False,
        "footageIds": ["take-1"],
        "releasedResourceIds": ["session-1", "surface-1"],
    }
    base.update(overrides)
    return base


class TcP01703(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P017-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "starting"})
        self.assertTrue(result["reasons"])

    def test_constants_encode_the_case(self):
        self.assertIn("halfway", _MODULE.INTERVENTION)
        self.assertIn("available footage", _MODULE.EXPECTED)
        self.assertIn("permanently starting", _MODULE.NEGATIVE)
        self.assertIn("recording", _MODULE.BOUNDARIES)
        self.assertIn("screen_attachment", _MODULE.INTERRUPTIONS)

    def test_permission_at_starting_without_audio_is_terminal(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "terminal")
        self.assertEqual(result["preservedResults"], ["take-1"])
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(any("audio not selected" in item for item in result["reasons"]))
        self.assertTrue(any("legal terminal" in item for item in result["reasons"]))
        self.assertTrue(any("session-1" in item for item in result["reasons"]))

    def test_camera_loss_during_recording_with_audio_keeps_footage(self):
        result = evaluate(
            payload(
                boundary="recording",
                interruption="camera_availability",
                audioSelected=True,
                footageIds=["take-av"],
                releasedResourceIds=["camera-1"],
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "terminal")
        self.assertEqual(result["preservedResults"], ["take-av"])
        self.assertTrue(any("audio selected" in item for item in result["reasons"]))
        self.assertTrue(any("recording" in item for item in result["reasons"]))

    def test_screen_attachment_at_preview_recovers(self):
        result = evaluate(
            payload(
                boundary="preview",
                interruption="screen_attachment",
                audioSelected=False,
                footageIds=["take-preview"],
            )
        )
        self.assertEqual(result["decision"], "recovery")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "starting"})
        self.assertEqual(result["preservedResults"], ["take-preview"])
        self.assertTrue(any("legal recovery" in item for item in result["reasons"]))

    def test_permanent_starting_is_rejected_and_footage_remains(self):
        result = evaluate(payload(boundary="configuring", permanentStarting=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["permanent-starting"])
        self.assertEqual(result["preservedResults"], ["take-1"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_silent_contract_switch_is_rejected(self):
        result = evaluate(
            payload(
                boundary="stopping",
                audioSelected=True,
                silentContractSwitch=True,
                footageIds=["take-stop"],
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], ["silent-contract-switch"])
        self.assertEqual(result["preservedResults"], ["take-stop"])

    def test_both_negatives_keep_footage(self):
        result = evaluate(payload(permanentStarting=True, silentContractSwitch=True, footageIds=[]))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(
            result["rejectedClaims"],
            ["permanent-starting", "silent-contract-switch"],
        )
        self.assertEqual(result["preservedResults"], [])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "boundary": "idle"},
            {**valid, "interruption": "thermal"},
            {**valid, "audioSelected": "yes"},
            {**valid, "footageIds": ["take-1", "take-1"]},
            {**valid, "releasedResourceIds": [""]},
            {k: v for k, v in valid.items() if k != "boundary"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
