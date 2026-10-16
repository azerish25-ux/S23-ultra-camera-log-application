"""Host checks for P125. Not a physical S23 probe."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p125_budget_disk_and_intermediate_storage",
    Path(__file__).resolve().parents[1] / "gates" / "p125_budget_disk_and_intermediate_storage.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
assess = _MODULE.assess
evaluate = _MODULE.evaluate

ROOT = Path(__file__).resolve().parents[2]
KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
SOURCE = 8_000_000_000
INTERMEDIATE = 4_000_000_000
SAFETY = 250_000_000
FREE = 20_000_000_000
FRAMES = 100
PER_FRAME = 40_000_000
RESERVE = SOURCE + INTERMEDIATE + SAFETY
HEADROOM = FREE - RESERVE


def document(**overrides):
    value = {
        "schemaVersion": 1,
        "phase": "P125",
        "implementationBaseRevision": "3fbad4bc0e0336e273d2723ec873f001e8865323",
        "evidenceId": "p125-raw-tenbit-duplication",
        "claim": "synthetic-host-fixture",
        "applyMutant": False,
        "source_bytes": SOURCE,
        "intermediate_estimate_bytes": INTERMEDIATE,
        "safety_bytes": SAFETY,
        "free_bytes": FREE,
        "start_allowed": True,
        "delete_source": False,
        "frame_count": FRAMES,
        "bytes_per_frame": PER_FRAME,
    }
    value.update(overrides)
    return value


def report(result):
    return result["preservedResults"][2]


class P125Tests(unittest.TestCase):
    def test_constants_match_the_phase_spec(self):
        self.assertEqual(_MODULE.BASE_REVISION, "3fbad4bc0e0336e273d2723ec873f001e8865323")
        self.assertEqual(_MODULE.PHASE, "P125")
        self.assertEqual(_MODULE.TITLE, "Budget disk and intermediate storage")
        self.assertEqual(_MODULE.WORKSTREAM, 16)
        self.assertEqual(_MODULE.DEPENDENCIES, ("P124",))
        self.assertEqual(
            _MODULE.GOAL,
            "Prevent high-quality development from filling storage and destroying recoverability.",
        )
        self.assertEqual(
            _MODULE.METHOD,
            "Estimate source, proxy, temporary, finalization, and publication requirements separately. "
            "Use conservative reserves and measured growth, not a fixed generic percentage. "
            "Allow explicit cleanup of reproducible intermediates while protecting originals and sole retained outputs.",
        )
        self.assertEqual(
            _MODULE.FIXTURE,
            "A long RAW source whose planned ten-bit export requires temporary duplication during publication.",
        )
        self.assertEqual(
            _MODULE.ORACLE,
            "The job declines or pauses safely before exhausting reserved space and explains which data can be removed safely.",
        )
        self.assertEqual(_MODULE.MUTANT, "Budget only the final output size and ignore temporary files.")
        self.assertEqual(_MODULE.DELIVERABLE, "Storage planner and low-space continuation policy")
        self.assertEqual(
            _MODULE.RESERVE_FORMULA,
            "reserve = source_bytes + intermediate_estimate_bytes + safety_bytes",
        )

    def test_reserve_formula_uses_explicit_safety_bytes(self):
        self.assertEqual(_MODULE.reserve_bytes(SOURCE, INTERMEDIATE, SAFETY), RESERVE)
        self.assertEqual(_MODULE.implied_intermediate_bytes(FRAMES, PER_FRAME), INTERMEDIATE)
        self.assertEqual(_MODULE.headroom_bytes(FREE, RESERVE), HEADROOM)
        self.assertEqual(RESERVE, 12_250_000_000)
        self.assertEqual(HEADROOM, 7_750_000_000)

    def test_fitting_budget_is_recorded(self):
        result = assess(document())
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "P125")
        self.assertEqual(result["decision"], "recorded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("p125-raw-tenbit-duplication", result["preservedResults"])
        kept = report(result)
        self.assertEqual(kept["reserveBytes"], RESERVE)
        self.assertEqual(kept["headroomBytes"], HEADROOM)
        self.assertEqual(kept["safety_bytes"], SAFETY)
        self.assertGreaterEqual(kept["headroomBytes"], 0)
        self.assertTrue(kept["policyStartAllowed"])
        self.assertFalse(kept["startRefused"])
        self.assertIn(_MODULE.ORACLE, " ".join(result["reasons"]))
        self.assertIn(_MODULE.RESERVE_FORMULA, result["reasons"])
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))
        self.assertIn("reproducible-intermediates", kept["removable"])
        self.assertIn("source-originals", kept["protected"])

    def test_fixture_file_and_handoff(self):
        payload = json.loads((ROOT / "docs" / "P125_BUDGET_DISK_AND_INTERMEDIATE_STORAGE.json").read_text())
        result = assess(payload)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(report(result)["reserveBytes"], RESERVE)
        self.assertEqual(report(result)["headroomBytes"], HEADROOM)
        note = (ROOT / "docs" / "P125_BUDGET_DISK_AND_INTERMEDIATE_STORAGE.md").read_text()
        self.assertIn("reserve = source_bytes + intermediate_estimate_bytes + safety_bytes", note)
        handoff = json.loads((ROOT / "docs" / "evidence" / "P125-handoff.json").read_text())
        self.assertEqual(handoff["phase"], "P125")
        self.assertEqual(handoff["nextPhase"], "P126")
        self.assertIsNone(handoff["commit"])
        self.assertEqual(handoff["failures"], 0)
        self.assertIn("physical S23 capture", handoff["unverified"])
        self.assertEqual(handoff["caseIds"][0], "TC-P125-01")
        self.assertEqual(handoff["caseIds"][-1], "TC-P125-08")

    def test_start_below_reserve_is_rejected_and_headroom_stays_negative(self):
        free = RESERVE - 250_000_000
        result = assess(document(free_bytes=free, start_allowed=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.START_BELOW_RESERVE, result["rejectedClaims"])
        self.assertIn("p125-raw-tenbit-duplication", result["preservedResults"])
        kept = report(result)
        self.assertEqual(kept["reserveBytes"], RESERVE)
        self.assertEqual(kept["headroomBytes"], free - RESERVE)
        self.assertLess(kept["headroomBytes"], 0)
        self.assertTrue(kept["startRefused"])
        self.assertFalse(kept["policyStartAllowed"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_refusing_start_when_space_is_short_is_recorded(self):
        free = RESERVE - 1
        result = assess(document(free_bytes=free, start_allowed=False, evidenceId="p125-pause"))
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        kept = report(result)
        self.assertEqual(kept["headroomBytes"], -1)
        self.assertTrue(kept["startRefused"])
        self.assertFalse(kept["policyStartAllowed"])
        self.assertIn("p125-pause", result["preservedResults"])
        self.assertIn("start refused before reserved space is exhausted", result["reasons"])

    def test_exact_reserve_may_start(self):
        result = assess(document(free_bytes=RESERVE))
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(report(result)["headroomBytes"], 0)
        self.assertTrue(report(result)["policyStartAllowed"])

    def test_delete_source_is_always_rejected(self):
        roomy = assess(document(free_bytes=10**15, delete_source=True, evidenceId="p125-keep-source"))
        self.assertEqual(roomy["decision"], "rejected")
        self.assertIn(_MODULE.DELETE_SOURCE, roomy["rejectedClaims"])
        self.assertGreaterEqual(report(roomy)["headroomBytes"], 0)
        self.assertIn("p125-keep-source", roomy["preservedResults"])
        self.assertIn("source-originals", report(roomy)["protected"])
        tight = assess(document(free_bytes=RESERVE - 1, start_allowed=True, delete_source=True))
        self.assertEqual(tight["decision"], "rejected")
        self.assertIn(_MODULE.DELETE_SOURCE, tight["rejectedClaims"])
        self.assertIn(_MODULE.START_BELOW_RESERVE, tight["rejectedClaims"])
        self.assertLess(report(tight)["headroomBytes"], 0)
        self.assertTrue(report(tight)["startRefused"])

    def test_zero_intermediate_with_positive_implication_is_rejected(self):
        result = assess(document(intermediate_estimate_bytes=0, start_allowed=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.IGNORED_INTERMEDIATES, result["rejectedClaims"])
        self.assertEqual(report(result)["impliedIntermediateBytes"], INTERMEDIATE)
        self.assertEqual(report(result)["intermediate_estimate_bytes"], 0)
        self.assertIn("p125-raw-tenbit-duplication", result["preservedResults"])
        reserve = _MODULE.reserve_bytes(SOURCE, 0, SAFETY)
        self.assertEqual(report(result)["reserveBytes"], reserve)

    def test_zero_intermediate_is_recorded_when_nothing_is_implied(self):
        result = assess(
            document(
                intermediate_estimate_bytes=0,
                frame_count=0,
                bytes_per_frame=PER_FRAME,
                evidenceId="p125-empty",
            )
        )
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(report(result)["impliedIntermediateBytes"], 0)
        self.assertEqual(report(result)["reserveBytes"], SOURCE + SAFETY)

    def test_positive_underestimate_is_not_the_zero_intermediate_mutant(self):
        result = assess(document(intermediate_estimate_bytes=1, bytes_per_frame=PER_FRAME))
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(report(result)["impliedIntermediateBytes"], INTERMEDIATE)
        self.assertNotIn(_MODULE.IGNORED_INTERMEDIATES, result["rejectedClaims"])

    def test_mutant_is_rejected_and_the_full_reserve_remains(self):
        result = assess(document(applyMutant=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.MUTANT, result["rejectedClaims"])
        self.assertEqual(report(result)["reserveBytes"], RESERVE)
        self.assertIn("p125-raw-tenbit-duplication", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_evaluate_uses_the_same_reserve(self):
        payload = document()
        payload.pop("schemaVersion")
        payload.pop("phase")
        payload.pop("implementationBaseRevision")
        payload["caseId"] = "P125"
        payload["evidenceId"] = "p125-evaluate"
        result = evaluate(payload)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["caseId"], "P125")
        self.assertEqual(report(result)["reserveBytes"], RESERVE)
        self.assertEqual(report(result)["headroomBytes"], HEADROOM)
        self.assertIn("p125-evaluate", result["preservedResults"])

    def test_negative_estimates_raise(self):
        for field in (
            "source_bytes",
            "intermediate_estimate_bytes",
            "safety_bytes",
            "free_bytes",
            "frame_count",
            "bytes_per_frame",
        ):
            with self.assertRaises(ValueError):
                assess(document(**{field: -1}))
        with self.assertRaises(ValueError):
            _MODULE.reserve_bytes(SOURCE, INTERMEDIATE, -1)
        with self.assertRaises(ValueError):
            _MODULE.reserve_bytes(True, 0, 0)
        with self.assertRaises(ValueError):
            assess(document(safety_bytes=1.0))
        with self.assertRaises(ValueError):
            assess(document(start_allowed=1))
        with self.assertRaises(ValueError):
            assess(document(delete_source=0))
        with self.assertRaises(ValueError):
            assess({})
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            assess(document(phase="P124"))
