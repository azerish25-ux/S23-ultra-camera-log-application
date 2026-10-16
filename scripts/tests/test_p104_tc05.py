"""Tests for TC-P104-05."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "p104_tc05",
    Path(__file__).resolve().parents[1] / "gates" / "p104_tc05.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p104-tc05",
        "config": "cpu",
        "delegateFailed": True,
        "fallback": "none",
        "uploadFrames": False,
        "depthDisabledReason": "delegate init failed",
    }
    base.update(overrides)
    return base


class TCP10405(unittest.TestCase):
    def assert_contract(self, result, evidence="p104-tc05"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P104-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertEqual(result["openQuestions"][0], "physical S23 measurement was not run")

    def test_good_disable_reason_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("depth-disabled-reason:delegate init failed", result["preservedResults"])
        explicit = evaluate(payload(config="gpu", fallback="explicit", depthDisabledReason=""))
        self.assertEqual(explicit["decision"], "recorded")
        self.assertNotEqual(explicit["decision"], "qualified")
        self.assertIn("fallback:explicit", explicit["preservedResults"])

    def test_negative_untested_backend_or_upload(self):
        untested = evaluate(payload(fallback="untested", config="accelerator"))
        self.assertEqual(untested["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, untested["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, untested["reasons"])
        self.assertIn("config:accelerator", untested["preservedResults"])
        upload = evaluate(payload(uploadFrames=True))
        self.assertEqual(upload["decision"], "rejected")
        self.assertIn("upload-frames:true", upload["preservedResults"])
        silent = evaluate(payload(fallback="none", depthDisabledReason=""))
        self.assertIn("missing-disable-reason", silent["rejectedClaims"])

    def test_evidence_change(self):
        evidence = "p104-tc05-gpu"
        result = evaluate(payload(evidenceId=evidence, config="gpu"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")
        healthy = evaluate(payload(delegateFailed=False, fallback="none", depthDisabledReason="", config="accelerator"))
        self.assertEqual(healthy["decision"], "recorded")

    def test_invalid_payload_raises(self):
        cases = (
            {},
            {**payload(), "applyNegative": True},
            payload(config="npu"),
            payload(fallback="qualified"),
            payload(uploadFrames="no"),
            payload(depthDisabledReason=" trailing"),
        )
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
