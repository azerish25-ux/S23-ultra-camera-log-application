"""TC-P062-08 consumer round-trip discrepancy."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p062_tc08", Path(__file__).resolve().parents[1] / "gates" / "p062_tc08.py"
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
        "sampleId": "round-1",
        "consumer": "independent-a",
        "consumerVersion": "1.2.3",
        "rangeSetting": "video",
        "sidecarAvailable": True,
        "opened": True,
        "compared": False,
        "numericDelta": "0",
        "tolerance": "0.01",
        "visualMatch": True,
    }
    base.update(overrides)
    return base


class TcP06208(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P062-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_packet_strings(self):
        self.assertEqual(
            _MODULE.NEGATIVE,
            "Successful file opening alone must not count as interoperability.",
        )

    def test_opening_alone_is_not_interoperability(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["open-is-not-interop"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("opened:yes", result["preservedResults"])
        self.assertIn("compared:no", result["preservedResults"])
        self.assertIn("delta:0", result["preservedResults"])
        self.assertIn("tolerance:0.01", result["preservedResults"])
        self.assertIn("round-1", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "within_tolerance"})

    def test_outside_tolerance_is_rejected(self):
        result = evaluate(payload(compared=True, numericDelta="0.02", visualMatch=False))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["outside-tolerance", "visual-mismatch"])
        self.assertIn("delta:0.02", result["preservedResults"])
        self.assertIn("version:1.2.3", result["preservedResults"])
        self.assertIn("range:video", result["preservedResults"])

    def test_repeat_consumer_versions_and_ranges(self):
        for version, range_setting in (("1.2.3", "video"), ("2.0.0", "full")):
            result = evaluate(
                payload(
                    compared=True,
                    consumerVersion=version,
                    rangeSetting=range_setting,
                    sampleId=version,
                )
            )
            self.assertEqual(result["decision"], "within_tolerance")
            self.assertEqual(result["rejectedClaims"], [])
            self.assertIn(f"version:{version}", result["preservedResults"])
            self.assertIn(f"range:{range_setting}", result["preservedResults"])
            self.assertIn("sidecar:yes", result["preservedResults"])
            self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_repeat_missing_sidecar_is_withheld(self):
        result = evaluate(payload(compared=True, sidecarAvailable=False, sampleId="no-side"))
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("sidecar:no", result["preservedResults"])
        self.assertIn("delta:0", result["preservedResults"])
        self.assertIn("visual:yes", result["preservedResults"])
        self.assertIn("sidecar availability is unresolved", result["openQuestions"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "within_tolerance"})

    def test_closed_file_is_not_a_round_trip(self):
        result = evaluate(payload(opened=False, compared=False))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["round-trip-not-run"])
        self.assertIn("opened:no", result["preservedResults"])
        self.assertIn("consumer:independent-a", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "tolerance"},
            {**valid, "extra": True},
            {**valid, "opened": "yes"},
            {**valid, "numericDelta": "-0.01"},
            {**valid, "tolerance": "0.010"},
            {**valid, "rangeSetting": "legal"},
            {**valid, "consumerVersion": ""},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
