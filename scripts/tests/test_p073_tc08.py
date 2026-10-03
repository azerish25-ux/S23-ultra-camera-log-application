"""TC-P073-08 clipped-source overclaim."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p073_tc08", Path(__file__).resolve().parents[1] / "gates" / "p073_tc08.py"
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
        "clipScope": "channel",
        "softShoulder": True,
        "appearanceApplied": True,
        "reportsRecoveredDetail": False,
        "missingDetailRetained": True,
    }
    base.update(overrides)
    return base


class TcP07308(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P073-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_packet_strings(self):
        self.assertIn("irreversibly clipped", _MODULE.INTERVENTION)
        self.assertIn("recovered sensor information", _MODULE.NEGATIVE)
        self.assertIn("individual channels", _MODULE.REPEAT)
        self.assertIn("white regions", _MODULE.REPEAT)

    def test_channel_clip_keeps_the_missing_detail_limitation(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "appearance_with_limitation")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("clip:channel", result["preservedResults"])
        self.assertIn("shoulder:true", result["preservedResults"])
        self.assertIn("missing-detail:true", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_white_clip_repeat_retains_the_limitation(self):
        result = evaluate(payload(clipScope="white"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "appearance_with_limitation")
        self.assertIn("clip:white", result["preservedResults"])
        self.assertIn("appearance:true", result["preservedResults"])
        self.assertIn("missing-detail:true", result["preservedResults"])

    def test_softer_highlight_is_not_recovered_sensor_information(self):
        result = evaluate(payload(reportsRecoveredDetail=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["recovered-detail"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("clip:channel", result["preservedResults"])
        self.assertIn("shoulder:true", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "appearance_with_limitation"})

    def test_white_recovered_detail_claim_keeps_the_clip_scope(self):
        result = evaluate(payload(clipScope="white", reportsRecoveredDetail=True, missingDetailRetained=False))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["recovered-detail"])
        self.assertIn("clip:white", result["preservedResults"])
        self.assertIn("missing-detail:false", result["preservedResults"])

    def test_dropped_limitation_is_rejected(self):
        result = evaluate(payload(missingDetailRetained=False))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["limitation-dropped"])
        self.assertIn("clip:channel", result["preservedResults"])

    def test_no_clip_is_withheld(self):
        result = evaluate(payload(clipScope="none"))
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("clip:none", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "clipScope"},
            {**valid, "extra": True},
            {**valid, "clipScope": "highlight"},
            {**valid, "softShoulder": "true"},
            {**valid, "appearanceApplied": 1},
            {**valid, "reportsRecoveredDetail": None},
            {**valid, "missingDetailRetained": "yes"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
