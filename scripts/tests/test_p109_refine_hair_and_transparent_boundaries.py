"""Host checks for P109. Not a physical S23 probe."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p109_refine_hair_and_transparent_boundaries",
    Path(__file__).resolve().parents[1] / "gates" / "p109_refine_hair_and_transparent_boundaries.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
assess = _MODULE.assess
evaluate = _MODULE.evaluate
refine = _MODULE.refine
MUTANT = _MODULE.MUTANT
ORACLE = _MODULE.ORACLE
BASE_REVISION = _MODULE.BASE_REVISION

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def _sample(confidence, klass, matte, colour="mixed", called_opaque=False):
    return {
        "confidence": confidence,
        "class": klass,
        "matte": matte,
        "colour": colour,
        "called_opaque": called_opaque,
    }


def document(**overrides):
    value = {
        "schemaVersion": 1,
        "phase": "P109",
        "implementationBaseRevision": "3fbad4bc0e0336e273d2723ec873f001e8865323",
        "evidenceId": "p109-hair-band",
        "claim": "synthetic-host-fixture",
        "hair_threshold": 0.5,
        "band": 1,
        "minimum_unknown_coverage": 1.0,
        "inpaint_glass": False,
        "foreground_colour": "foreground",
        "samples": [
            _sample(0.99, "opaque", 1.0, "subject", True),
            _sample(0.99, "opaque", "unknown", "subject", False),
            _sample(0.2, "hair", 0.42, "mixed", False),
            _sample(0.8, "glass", 0.3, "mixed", False),
            _sample(0.99, "background", "unknown", "background", False),
            _sample(0.99, "background", 0.0, "background", False),
        ],
        "applyMutant": False,
    }
    value.update(overrides)
    return value


class P109Tests(unittest.TestCase):
    def assert_contract(self, result, evidence="p109-hair-band"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "P109")
        self.assertIn(result["decision"], {"recorded", "rejected"})
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("synthetic-host-fixture", result["preservedResults"])
        self.assertIn(ORACLE, " ".join(result["reasons"]))
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))

    def test_partial_unknown_band_is_recorded_not_qualified(self):
        result = assess(document())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("unknown-band 1,2,3,4", result["reasons"])
        self.assertIn("unknown-coverage 1.000000", result["reasons"])
        self.assertEqual(evaluate(document())["decision"], "recorded")

    def test_mutant_is_rejected_and_evidence_remains(self):
        result = assess(document(applyMutant=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(MUTANT, result["rejectedClaims"])

    def test_hard_matte_on_hair_and_transparent_is_rejected(self):
        result = assess(document(
            band=0,
            samples=[
                _sample(0.2, "hair", 0.0, "mixed", False),
                _sample(0.2, "transparent", 1.0, "mixed", False),
            ],
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("hard-matte-on-hair-or-transparent", result["rejectedClaims"])
        self.assertIn("unknown-band-hard-matte", result["rejectedClaims"])

    def test_unknown_band_foreground_opaque_is_rejected(self):
        result = assess(document(
            band=0,
            minimum_unknown_coverage=0.0,
            samples=[_sample(0.2, "hair", 0.4, "foreground", True)],
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("unknown-band-replaced-by-foreground-and-called-opaque", result["rejectedClaims"])
        self.assertNotIn("unknown-coverage-below-minimum", result["rejectedClaims"])

    def test_coverage_below_minimum_is_rejected(self):
        result = assess(document(
            band=0,
            minimum_unknown_coverage=0.75,
            samples=[
                _sample(0.2, "hair", 0.4, "mixed", False),
                _sample(0.2, "glass", 0.4, "mixed", True),
            ],
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["unknown-coverage-below-minimum"])

    def test_inpaint_glass_is_rejected(self):
        result = assess(document(inpaint_glass=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("inpaint_glass", result["rejectedClaims"])

    def test_band_radius_expands_low_confidence_and_mixed_classes(self):
        inside = document(samples=[
            _sample(0.99, "opaque", 1.0, "subject", True),
            _sample(0.99, "opaque", 1.0, "subject", True),
            _sample(0.2, "hair", 0.42, "mixed", False),
            _sample(0.8, "glass", 0.3, "mixed", False),
            _sample(0.99, "background", "unknown", "background", False),
            _sample(0.99, "background", 0.0, "background", False),
        ])
        result = assess(inside)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("unknown-band-hard-matte", result["rejectedClaims"])
        self.assertIn("unknown-band 1,2,3,4", result["reasons"])

    def test_refine_does_not_emit_hard_matte_or_call_foreground_opaque(self):
        refined = refine(
            [
                _sample(0.2, "hair", 1.0, "foreground", True),
                _sample(0.9, "glass", 0.0, "scene", False),
            ],
            0.5,
            1,
            foreground_colour="foreground",
        )
        self.assertTrue(all(item["matte"] == "unknown" for item in refined))
        self.assertTrue(all(item["called_opaque"] is False for item in refined))
        self.assertEqual(refined[0]["colour"], "foreground")
        self.assertEqual(refined[1]["colour"], "scene")
        wrapped = document(band=1, samples=refined, minimum_unknown_coverage=1.0)
        result = assess(wrapped)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])

    def test_non_finite_sample_raises(self):
        with self.assertRaises(ValueError):
            assess(document(samples=[_sample(float("nan"), "hair", 0.4)]))

    def test_base_revision_constant(self):
        self.assertEqual(BASE_REVISION, "3fbad4bc0e0336e273d2723ec873f001e8865323")

    def test_fixture_json_is_recorded(self):
        path = Path(__file__).resolve().parents[2] / "docs" / "P109_REFINE_HAIR_AND_TRANSPARENT_BOUNDARIES.json"
        fixture = json.loads(path.read_text(encoding="utf-8"))
        result = assess(fixture)
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("p109-hair-band", result["preservedResults"])
        self.assertIn("unknown-band 1,2,3,4", result["reasons"])
