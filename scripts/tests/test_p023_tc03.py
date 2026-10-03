"""TC-P023-03 interruptions at transition boundaries."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "p023_tc03", Path(__file__).resolve().parents[1] / "gates" / "p023_tc03.py"
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
        "boundary": "idle_to_opening",
        "audioSelected": True,
        "interrupt": "permission",
        "terminal": "stopped",
        "resourcesReleased": True,
        "footageRetained": True,
        "footageId": "footage-1",
        "silentContractSwitch": False,
    }
    base.update(overrides)
    return base


class TcP02303(unittest.TestCase):
    def assert_contract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P023-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_module_encodes_case_text(self):
        self.assertIn("asynchronous transition", _MODULE.INTERVENTION)
        self.assertIn("available footage retained", _MODULE.EXPECTED)
        self.assertIn("permanently starting", _MODULE.NEGATIVE)
        self.assertIn("idle_to_opening", _MODULE.BOUNDARIES)
        self.assertIn("stopping_to_final", _MODULE.BOUNDARIES)

    def test_idle_to_opening_with_audio_stops_and_keeps_selection(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "stopped")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"], ["footage-1", "audio-selected"])
        self.assertTrue(any(_MODULE.EXPECTED in item for item in result["reasons"]))

    def test_starting_to_active_without_audio_can_fail_visibly(self):
        result = evaluate(
            payload(
                boundary="starting_to_active",
                audioSelected=False,
                interrupt="camera_availability",
                terminal="failed",
                footageId="footage-video",
            )
        )
        self.assert_contract(result)
        self.assertEqual(result["decision"], "failed_visible")
        self.assertEqual(result["preservedResults"], ["footage-video", "audio-not-selected"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_active_to_stopping_with_audio_recovers(self):
        result = evaluate(
            payload(
                boundary="active_to_stopping",
                audioSelected=True,
                interrupt="screen_attachment",
                terminal="recovered",
                footageId="footage-live",
            )
        )
        self.assertEqual(result["decision"], "recovered")
        self.assertIn("audio-selected", result["preservedResults"])
        self.assertIn("footage-live", result["preservedResults"])

    def test_permanently_starting_is_rejected(self):
        result = evaluate(
            payload(boundary="configured_to_starting", terminal="starting", footageId="footage-stuck")
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "stopped"})
        self.assertIn("permanently-starting", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"], ["footage-stuck", "audio-selected"])
        self.assertTrue(any(_MODULE.NEGATIVE in item for item in result["reasons"]))

    def test_silent_contract_switch_keeps_audio_selection_in_inventory(self):
        result = evaluate(
            payload(
                boundary="opening_to_configured",
                audioSelected=True,
                terminal="switched",
                silentContractSwitch=True,
                footageId="footage-switch",
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("silent-contract-switch", result["rejectedClaims"])
        self.assertIn("audio-selected", result["preservedResults"])
        self.assertIn("footage-switch", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_dropped_footage_is_rejected_but_id_remains(self):
        result = evaluate(payload(boundary="stopping_to_final", footageRetained=False, audioSelected=False))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("footage-dropped", result["rejectedClaims"])
        self.assertIn("footage-1", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {**valid, "boundary": "middle"},
            {**valid, "interrupt": "disk"},
            {**valid, "terminal": "qualified"},
            {**valid, "audioSelected": "yes"},
            {**valid, "footageId": ""},
            {**valid, "extra": False},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
