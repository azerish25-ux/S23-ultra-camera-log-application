"""TC-P072-03 in-flight resource reuse."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p072_tc03", Path(__file__).resolve().parents[1] / "gates" / "p072_tc03.py"
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
        "resourceId": "tile-a",
        "kind": "texture",
        "completionDelayed": True,
        "recycleImmediate": False,
        "ownershipHeld": True,
        "synchronized": True,
        "outputState": "none",
        "site": "baseline",
    }
    base.update(overrides)
    return base


class TcP07203(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P072-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_packet_strings(self):
        self.assertIn("command submission", _MODULE.NEGATIVE)
        self.assertIn("cancellation", _MODULE.REPEAT)

    def test_delayed_completion_holds_ownership(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "ownership_held")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("tile-a", result["preservedResults"])
        self.assertIn("kind:texture", result["preservedResults"])
        self.assertIn("output:none", result["preservedResults"])

    def test_immediate_recycle_fails_and_keeps_the_resource(self):
        result = evaluate(payload(recycleImmediate=True, outputState="fresh"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["immediate-recycle"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("tile-a", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "ownership_held"})

    def test_stale_output_is_rejected_with_the_resource_kept(self):
        result = evaluate(payload(outputState="partial", kind="buffer"))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["stale-or-partial-output"])
        self.assertIn("kind:buffer", result["preservedResults"])
        self.assertIn("output:partial", result["preservedResults"])

    def test_repeat_cancellation(self):
        result = evaluate(payload(site="cancellation", resourceId="buf-1", kind="buffer"))
        self.assertEqual(result["decision"], "ownership_held")
        self.assertIn("site:cancellation", result["preservedResults"])
        self.assertIn("buf-1", result["preservedResults"])

    def test_repeat_context_loss_and_mode_switch(self):
        for site in ("context-loss", "mode-switch"):
            result = evaluate(payload(site=site))
            self.assertEqual(result["decision"], "ownership_held")
            self.assertIn(f"site:{site}", result["preservedResults"])
            self.assertIn("tile-a", result["preservedResults"])

    def test_missing_sync_is_withheld(self):
        result = evaluate(payload(synchronized=False))
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("synchronized:false", result["preservedResults"])
        self.assertIn("tile-a", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "kind": "image"},
            {**valid, "outputState": "ready"},
            {**valid, "site": "warm"},
            {**valid, "ownershipHeld": "true"},
            {k: v for k, v in valid.items() if k != "resourceId"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
