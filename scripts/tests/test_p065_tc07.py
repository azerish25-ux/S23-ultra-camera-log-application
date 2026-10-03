"""TC-P065-07 graphics context loss."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p065_tc07", Path(__file__).resolve().parents[1] / "gates" / "p065_tc07.py"
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
        "phase": "rendering",
        "site": "baseline",
        "contextInvalid": True,
        "staleHandles": False,
        "publishedUnverified": False,
        "leaked": False,
        "state": "recovered",
        "sourceRetained": True,
        "queuedJob": False,
    }
    base.update(overrides)
    return base


class TcP06507(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P065-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_packet_strings(self):
        self.assertIn("stale handles", _MODULE.NEGATIVE)
        self.assertIn("queued development job", _MODULE.REPEAT)

    def test_recovery_is_a_defined_state(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "defined_state")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("phase:rendering", result["preservedResults"])
        self.assertIn("state:recovered", result["preservedResults"])
        self.assertIn("source:true", result["preservedResults"])

    def test_stale_handles_fail_and_keep_source_and_job(self):
        result = evaluate(payload(staleHandles=True, site="queued-job", queuedJob=True, state="recovered"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["stale-handles"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("source:true", result["preservedResults"])
        self.assertIn("queued:true", result["preservedResults"])
        self.assertIn("state:recovered", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "defined_state"})

    def test_defined_failure_does_not_publish(self):
        result = evaluate(payload(state="failed", phase="cleanup"))
        self.assertEqual(result["decision"], "defined_state")
        self.assertIn("state:failed", result["preservedResults"])
        self.assertIn("phase:cleanup", result["preservedResults"])
        self.assertEqual(result["rejectedClaims"], [])

    def test_repeat_source_retained(self):
        result = evaluate(payload(site="source-retained", phase="initialization", sourceRetained=True))
        self.assertEqual(result["decision"], "defined_state")
        self.assertIn("site:source-retained", result["preservedResults"])
        self.assertIn("source:true", result["preservedResults"])

    def test_repeat_queued_job(self):
        result = evaluate(payload(site="queued-job", queuedJob=True))
        self.assertEqual(result["decision"], "defined_state")
        self.assertIn("site:queued-job", result["preservedResults"])
        self.assertIn("queued:true", result["preservedResults"])

    def test_unverified_frame_and_leak_are_rejected(self):
        result = evaluate(payload(publishedUnverified=True, leaked=True, state="undefined"))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(
            result["rejectedClaims"],
            ["unverified-frames", "resource-leak", "undefined-state"],
        )
        self.assertIn("source:true", result["preservedResults"])
        self.assertIn("phase:rendering", result["preservedResults"])

    def test_valid_context_is_withheld(self):
        result = evaluate(payload(contextInvalid=False))
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("context-invalid:false", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "phase": "draw"},
            {**valid, "state": "lost"},
            {**valid, "staleHandles": "no"},
            {**valid, "site": "source_retained"},
            {k: v for k, v in valid.items() if k != "queuedJob"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
