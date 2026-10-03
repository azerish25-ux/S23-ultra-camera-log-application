"""TC-P069-04 tile seam stress."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p069_tc04", Path(__file__).resolve().parents[1] / "gates" / "p069_tc04.py"
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
        "tileId": "tile-0",
        "site": "boundary",
        "halo": "4",
        "requiredHalo": "2",
        "globalCoordinates": True,
        "overlap": True,
        "localSeed": False,
        "delta": "0.01",
        "tolerance": "0.05",
        "referenceId": "untiled",
    }
    base.update(overrides)
    return base


class TcP06904(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P069-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_packet_strings(self):
        self.assertIn("tile-local random seeds", _MODULE.NEGATIVE)
        self.assertIn("maximum configured blur", _MODULE.REPEAT)

    def test_boundary_matches_untiled_reference(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "seam_matched")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("tile-0", result["preservedResults"])
        self.assertIn("reference:untiled", result["preservedResults"])
        self.assertIn("delta:0.01", result["preservedResults"])

    def test_local_seed_and_missing_overlap_fail(self):
        result = evaluate(payload(localSeed=True, overlap=False))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["tile-local-seed", "missing-overlap"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("reference:untiled", result["preservedResults"])
        self.assertIn("tile-0", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "seam_matched"})

    def test_repeat_corner(self):
        result = evaluate(payload(site="corner", tileId="corner-tile"))
        self.assertEqual(result["decision"], "seam_matched")
        self.assertIn("site:corner", result["preservedResults"])
        self.assertIn("corner-tile", result["preservedResults"])

    def test_repeat_varied_size_and_max_blur(self):
        varied = evaluate(payload(site="varied-size", halo="8", requiredHalo="8"))
        blur = evaluate(payload(site="max-blur", halo="16", requiredHalo="16", delta="0.05"))
        self.assertEqual(varied["decision"], "seam_matched")
        self.assertEqual(blur["decision"], "seam_matched")
        self.assertIn("site:varied-size", varied["preservedResults"])
        self.assertIn("site:max-blur", blur["preservedResults"])
        self.assertIn("reference:untiled", blur["preservedResults"])

    def test_short_halo_and_large_delta_keep_the_reference(self):
        result = evaluate(payload(halo="1", delta="0.2"))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["halo-short", "seam-mismatch"])
        self.assertIn("reference:untiled", result["preservedResults"])
        self.assertIn("halo:1", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "halo": "04"},
            {**valid, "tolerance": "0"},
            {**valid, "delta": "-0.01"},
            {**valid, "site": "edge"},
            {**valid, "localSeed": 0},
            {**valid, "referenceId": ""},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
