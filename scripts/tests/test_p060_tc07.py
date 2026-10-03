"""TC-P060-07 double viewing transform."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p060_tc07", Path(__file__).resolve().parents[1] / "gates" / "p060_tc07.py"
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
        "sourceTag": "logc3",
        "tagOrigin": "manual",
        "preview": "viewing",
        "development": "viewing",
        "patch": "grey",
        "thumbnailAgrees": True,
    }
    base.update(overrides)
    return base


class TcP06007(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P060-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.EXPECTED, result["reasons"])
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])

    def test_packet_strings(self):
        self.assertIn("thumbnail", _MODULE.NEGATIVE)
        self.assertIn("manual editor", _MODULE.REPEAT)

    def test_double_view_rejects_and_keeps_both_branches(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("double-viewing-transform", result["rejectedClaims"])
        self.assertIn("thumbnail-not-interpretation", result["rejectedClaims"])
        self.assertIn("clean:0.180000", result["preservedResults"])
        self.assertIn("rendered:0.489437", result["preservedResults"])
        self.assertIn("doubled:0.742518", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_thumbnail_alone_does_not_certify(self):
        result = evaluate(payload(preview="viewing", development="identity", thumbnailAgrees=True))
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], ["thumbnail-not-interpretation"])
        self.assertIn("clean:0.180000", result["preservedResults"])
        self.assertIn("rendered:0.489437", result["preservedResults"])
        self.assertIn("doubled:not-applied", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "branches_separated"})

    def test_single_view_separates_branches(self):
        result = evaluate(payload(development="identity", thumbnailAgrees=False, patch="red"))
        self.assertEqual(result["decision"], "branches_separated")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("clean:0.800000", result["preservedResults"])
        self.assertIn("rendered:0.911215", result["preservedResults"])
        self.assertIn("patch:red", result["preservedResults"])

    def test_repeat_manual_assignment(self):
        result = evaluate(payload(tagOrigin="manual", patch="red", thumbnailAgrees=False))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("origin:manual", result["preservedResults"])
        self.assertIn("clean:0.800000", result["preservedResults"])
        self.assertIn("rendered:0.911215", result["preservedResults"])

    def test_repeat_automatic_source_tag(self):
        result = evaluate(
            payload(tagOrigin="automatic", sourceTag="display-709", thumbnailAgrees=False, patch="grey")
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("origin:automatic", result["preservedResults"])
        self.assertIn("source:display-709", result["preservedResults"])
        self.assertIn("doubled:0.742518", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {**valid, "patch": "blue"},
            {**valid, "tagOrigin": "sidecar"},
            {**valid, "thumbnailAgrees": "yes"},
            {k: v for k, v in valid.items() if k != "preview"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
