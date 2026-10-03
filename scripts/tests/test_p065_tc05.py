"""TC-P065-05 temporal chunk discontinuity."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p065_tc05", Path(__file__).resolve().parents[1] / "gates" / "p065_tc05.py"
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
        "chunkId": "chunk-3",
        "site": "boundary",
        "movingObject": True,
        "focusTransition": True,
        "emptyHistory": False,
        "contextReconstructed": True,
        "frameCount": "1",
        "duplicateFrame": False,
        "stableTemporal": True,
    }
    base.update(overrides)
    return base


class TcP06505(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P065-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_packet_strings(self):
        self.assertIn("Empty-history", _MODULE.NEGATIVE)
        self.assertIn("scene cuts", _MODULE.REPEAT)

    def test_reconstructed_context_emits_one_frame(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "context_reconstructed")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("chunk-3", result["preservedResults"])
        self.assertIn("frames:1", result["preservedResults"])

    def test_empty_history_restart_fails_and_keeps_the_chunk(self):
        result = evaluate(payload(emptyHistory=True, contextReconstructed=False))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("empty-history-restart", result["rejectedClaims"])
        self.assertIn("missing-context", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("chunk-3", result["preservedResults"])
        self.assertIn("frames:1", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "context_reconstructed"})

    def test_repeat_scene_cut(self):
        result = evaluate(payload(site="scene-cut", chunkId="cut-1"))
        self.assertEqual(result["decision"], "context_reconstructed")
        self.assertIn("site:scene-cut", result["preservedResults"])
        self.assertIn("cut-1", result["preservedResults"])

    def test_repeat_overlap_trim_and_replaced_model(self):
        overlap = evaluate(payload(site="overlap-trim"))
        replaced = evaluate(payload(site="replaced-model", chunkId="model-b"))
        self.assertEqual(overlap["decision"], "context_reconstructed")
        self.assertEqual(replaced["decision"], "context_reconstructed")
        self.assertIn("site:overlap-trim", overlap["preservedResults"])
        self.assertIn("site:replaced-model", replaced["preservedResults"])
        self.assertIn("model-b", replaced["preservedResults"])

    def test_duplicate_frame_is_rejected(self):
        result = evaluate(payload(frameCount="2", duplicateFrame=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["frame-not-once"])
        self.assertIn("frames:2", result["preservedResults"])
        self.assertIn("chunk-3", result["preservedResults"])

    def test_incomplete_boundary_is_withheld(self):
        result = evaluate(payload(movingObject=False))
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("moving:false", result["preservedResults"])
        self.assertIn("chunk-3", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "frameCount": "0"},
            {**valid, "frameCount": "01"},
            {**valid, "site": "cut"},
            {**valid, "emptyHistory": "no"},
            {k: v for k, v in valid.items() if k != "chunkId"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
