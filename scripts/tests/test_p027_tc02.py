"""TC-P027-02 matching units are not clock equivalence."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p027_tc02", Path(__file__).resolve().parents[1] / "gates" / "p027_tc02.py"
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
        "leftDomain": "sensor",
        "rightDomain": "audio_hardware",
        "leftUnits": "ns",
        "rightUnits": "ns",
        "leftValue": "1000",
        "rightValue": "1000",
        "originChanged": False,
        "mappingPresent": False,
        "subtractedUnrelated": False,
        "claimsEquivalence": False,
    }
    base.update(overrides)
    return base


class TcP02702(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P027-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_module_encodes_the_case_text(self):
        self.assertIn("plausible-looking numerical", _MODULE.INTERVENTION)
        self.assertIn("timing unverified", _MODULE.EXPECTED)
        self.assertIn("numeric units", _MODULE.NEGATIVE)
        self.assertIn("sensor", _MODULE.DOMAINS)
        self.assertIn("audio_hardware", _MODULE.DOMAINS)
        self.assertIn("monotonic_system", _MODULE.DOMAINS)
        self.assertIn("encoded_presentation", _MODULE.DOMAINS)

    def test_sensor_and_audio_hardware_units_stay_unverified(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "unverified")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"], ["sensor", "audio_hardware", "1000", "1000"])
        self.assertTrue(any("unverified" in item for item in result["reasons"]))

    def test_monotonic_and_presentation_units_do_not_establish_equivalence(self):
        result = evaluate(
            payload(
                leftDomain="monotonic_system",
                rightDomain="encoded_presentation",
                leftValue="50",
                rightValue="50",
                claimsEquivalence=True,
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "unverified", "mapped"})
        self.assertEqual(result["rejectedClaims"], ["numeric-units-not-equivalence"])
        self.assertEqual(result["preservedResults"], ["monotonic_system", "encoded_presentation", "50", "50"])

    def test_subtracting_unrelated_clocks_is_rejected_and_values_remain(self):
        result = evaluate(payload(subtractedUnrelated=True, claimsEquivalence=True, originChanged=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(
            result["rejectedClaims"],
            ["unrelated-clock-subtraction", "numeric-units-not-equivalence"],
        )
        self.assertIn("1000", result["preservedResults"])
        self.assertIn("sensor", result["preservedResults"])
        self.assertIn("audio_hardware", result["preservedResults"])

    def test_an_identified_mapping_is_not_qualification(self):
        result = evaluate(payload(mappingPresent=True, originChanged=True))
        self.assertEqual(result["decision"], "mapped")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][:2], ["sensor", "audio_hardware"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {**valid, "leftDomain": "audio"},
            {**valid, "leftDomain": "sensor", "rightDomain": "sensor"},
            {**valid, "leftValue": "010"},
            {**valid, "leftUnits": "nanoseconds"},
            {**valid, "mappingPresent": 1},
            {k: v for k, v in valid.items() if k != "rightValue"},
            {**valid, "extra": True},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
