"""TC-P046-07 unrecorded measurement conditions."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p046_tc07", Path(__file__).resolve().parents[1] / "gates" / "p046_tc07.py"
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
        "recordId": "cal-1",
        "illuminant": "D65",
        "exposure": "10ms",
        "targetIdentity": "gray-18",
        "sourceRevision": "rev-a",
        "attractiveColor": False,
        "origin": "measurement",
        "requestDefault": False,
        "samples": ["patch-a", "patch-b"],
    }
    base.update(overrides)
    return base


class TcP04607(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P046-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_recorded_context_is_not_a_default_profile(self):
        result = evaluate(payload(requestDefault=True, attractiveColor=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "context_recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("sample:patch-a", result["preservedResults"])
        self.assertIn("illuminant:D65", result["preservedResults"])
        self.assertIn("exploratory", _MODULE.EXPECTED)

    def test_missing_illuminant_is_downgraded_and_samples_remain(self):
        result = evaluate(payload(illuminant=""))
        self.assertEqual(result["decision"], "downgraded")
        self.assertIn("measurement-claim", result["rejectedClaims"])
        self.assertIn("missing:illuminant", result["rejectedClaims"])
        self.assertIn("illuminant:missing", result["preservedResults"])
        self.assertIn("sample:patch-b", result["preservedResults"])
        self.assertIn("retained for exploratory research", result["openQuestions"])

    def test_author_assertion_repeat_cannot_become_default(self):
        result = evaluate(
            payload(origin="author-assertion", attractiveColor=True, requestDefault=True, illuminant="")
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "context_recorded"})
        self.assertIn("default-measured-profile", result["rejectedClaims"])
        self.assertIn("author-assertion", result["rejectedClaims"])
        self.assertIn("attractive-without-context", result["rejectedClaims"])
        self.assertIn("sample:patch-a", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_manufacturer_metadata_repeat_cannot_become_default(self):
        result = evaluate(
            payload(
                origin="manufacturer-metadata",
                attractiveColor=True,
                requestDefault=True,
                sourceRevision="",
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("manufacturer-metadata", result["rejectedClaims"])
        self.assertIn("default-measured-profile", result["rejectedClaims"])
        self.assertIn("missing:source-revision", result["rejectedClaims"])
        self.assertIn("source-revision:missing", result["preservedResults"])
        self.assertIn("sample:patch-b", result["preservedResults"])

    def test_attractive_result_without_request_is_downgraded(self):
        result = evaluate(payload(exposure="", attractiveColor=True, requestDefault=False))
        self.assertEqual(result["decision"], "downgraded")
        self.assertIn("attractive-without-context", result["rejectedClaims"])
        self.assertIn("exposure:missing", result["preservedResults"])
        self.assertNotIn("default-measured-profile", result["rejectedClaims"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "origin"},
            {**valid, "extra": True},
            {**valid, "origin": "rumor"},
            {**valid, "samples": []},
            {**valid, "samples": ["has space"]},
            {**valid, "illuminant": "D 65"},
            {**valid, "requestDefault": "yes"},
            {**valid, "attractiveColor": 1},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
