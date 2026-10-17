"""Host checks for P131. Not a physical S23 probe."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "p131_design_manual_controls_for_deliberate_operation",
    Path(__file__).resolve().parents[1]
    / "gates"
    / "p131_design_manual_controls_for_deliberate_operation.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
assess = _MODULE.assess

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def load_document() -> dict:
    return json.loads(
        (
            _ROOT / "docs" / "P131_DESIGN_MANUAL_CONTROLS_FOR_DELIBERATE_OPERATION.json"
        ).read_text(encoding="utf-8")
    )


def document(**overrides):
    value = _MODULE.fixture_document()
    value.update(overrides)
    return value


def proposed_with(**overrides):
    value = document()
    proposed = dict(value["proposed"])
    proposed.update(overrides)
    value["proposed"] = proposed
    return value


def control(result):
    return result["preservedResults"][1]


class P131Tests(unittest.TestCase):
    def test_phase_constants_match_the_spec(self):
        self.assertEqual(_MODULE.BASE_REVISION, "db5593a4c7dae4d23363e70a27f0f93c3eb07b2b")
        self.assertEqual(_MODULE.PHASE, "P131")
        self.assertEqual(_MODULE.WORKSTREAM, 17)
        self.assertEqual(_MODULE.TITLE, "Design manual controls for deliberate operation")
        self.assertEqual(
            _MODULE.GOAL,
            "Offer precise adjustment without accidental changes during a take.",
        )
        self.assertEqual(
            _MODULE.METHOD,
            "Provide bounded sliders, numeric entry, reset, and explicit apply behavior where needed. "
            "Keep units visible and disable unavailable controls with reasons. Distinguish draft values "
            "from committed effective targets and observed sensor results.",
        )
        self.assertEqual(
            _MODULE.FIXTURE,
            "A user types an invalid shutter value, rotates the phone, and then returns to the controls.",
        )
        self.assertEqual(
            _MODULE.ORACLE,
            "The invalid draft is not applied, valid state survives appropriately, and the source "
            "recording configuration remains unchanged.",
        )
        self.assertEqual(
            _MODULE.MUTANT,
            "Apply every partially typed numeric string immediately to the camera.",
        )
        self.assertEqual(_MODULE.DELIVERABLE, "Manual interaction contract and draft-state tests")
        self.assertEqual(_MODULE.DEPENDENCIES, ("P130",))

    def test_fixture_records_the_invalid_shutter_draft(self):
        source = load_document()
        self.assertEqual(source, _MODULE.fixture_document())
        result = assess(source)
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "P131")
        self.assertEqual(result["decision"], "recorded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn(source["evidenceId"], result["preservedResults"])
        self.assertIn(source["claim"], result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn(_MODULE.ORACLE, " ".join(result["reasons"]))
        self.assertIn(_MODULE.DRAFT_RULE, result["reasons"])
        record = control(result)
        self.assertEqual(record["draft"], "1.")
        self.assertEqual(record["draftKind"], "incomplete")
        self.assertEqual(record["draftStatus"], "held")
        self.assertEqual(record["applied"], 180)
        self.assertEqual(record["previousApplied"], 180)
        self.assertEqual(record["source_configuration"], "1080p-sdr")
        self.assertTrue(record["record_enabled"])
        self.assertTrue(record["stop_enabled"])
        self.assertEqual(record["orientation"], "landscape")
        self.assertEqual(record["unit"], "deg")
        self.assertFalse(record["apply_partial"])
        self.assertIn("orientation portrait -> landscape", result["reasons"])

    def test_partial_strings_do_not_change_the_applied_value(self):
        for draft in ("1.", "", "1. ", ".", "+", "nan"):
            result = assess(proposed_with(draft=draft, submitted=True, applied=180))
            self.assertEqual(result["decision"], "recorded", draft)
            self.assertEqual(result["rejectedClaims"], [], draft)
            record = control(result)
            self.assertEqual(record["applied"], 180, draft)
            self.assertEqual(record["previousApplied"], 180, draft)
            self.assertEqual(record["draft"], draft)
            self.assertNotEqual(record["draftKind"], "complete", draft)
            self.assertEqual(record["draftStatus"], "partial", draft)

    def test_explicit_in_range_submit_updates_the_applied_value(self):
        result = assess(proposed_with(draft="90", submitted=True, applied=90))
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        record = control(result)
        self.assertEqual(record["applied"], 90)
        self.assertEqual(record["previousApplied"], 180)
        self.assertEqual(record["candidateApplied"], 90)
        self.assertEqual(record["draftStatus"], "applied")
        self.assertEqual(record["draftKind"], "complete")
        self.assertEqual(record["source_configuration"], "1080p-sdr")
        self.assertTrue(record["record_enabled"])
        self.assertTrue(record["stop_enabled"])

    def test_inclusive_bounds_and_empty_hold(self):
        low = assess(proposed_with(draft="1", submitted=True, applied=1))
        high = assess(proposed_with(draft="360", submitted=True, applied=360))
        self.assertEqual(control(low)["applied"], 1)
        self.assertEqual(control(high)["applied"], 360)
        self.assertEqual(low["decision"], "recorded")
        self.assertEqual(high["decision"], "recorded")
        scientific = assess(proposed_with(draft="1e2", submitted=True, applied=100))
        self.assertEqual(scientific["decision"], "recorded")
        self.assertEqual(control(scientific)["applied"], 100)

    def test_out_of_range_submit_is_rejected_and_keeps_the_previous_value(self):
        for draft, claimed in (("900", 900), ("0", 0), ("361", 180), ("-5", 180)):
            result = assess(proposed_with(draft=draft, submitted=True, applied=claimed))
            self.assertEqual(result["decision"], "rejected", draft)
            self.assertNotIn(result["decision"], {"qualified", "allowed"})
            self.assertIn(_MODULE.OUT_OF_RANGE_SUBMIT, result["rejectedClaims"])
            self.assertNotIn(_MODULE.PARTIAL_REACHED, result["rejectedClaims"])
            record = control(result)
            self.assertEqual(record["applied"], 180, draft)
            self.assertEqual(record["previousApplied"], 180, draft)
            self.assertEqual(record["source_configuration"], "1080p-sdr")
            self.assertIn("p131-manual-controls", result["preservedResults"])

    def test_apply_partial_keystrokes_are_rejected(self):
        partial = assess(proposed_with(draft="1.", apply_partial=True, applied=180))
        self.assertEqual(partial["decision"], "rejected")
        self.assertIn(_MODULE.APPLY_PARTIAL, partial["rejectedClaims"])
        self.assertIn(_MODULE.PARTIAL_REACHED, partial["rejectedClaims"])
        self.assertIn(_MODULE.MUTANT, partial["reasons"])
        self.assertEqual(control(partial)["applied"], 180)
        moved = assess(proposed_with(draft="90", submitted=True, apply_partial=True, applied=90))
        self.assertEqual(moved["decision"], "rejected")
        self.assertIn(_MODULE.APPLY_PARTIAL, moved["rejectedClaims"])
        self.assertIn(_MODULE.APPLIED_DIVERGED, moved["rejectedClaims"])
        self.assertEqual(control(moved)["applied"], 180)
        self.assertEqual(control(moved)["candidateApplied"], 180)

    def test_apply_mutant_rolls_back_even_a_complete_submit(self):
        result = assess(
            document(
                applyMutant=True,
                proposed=_MODULE.held_proposal(draft="90", submitted=True, applied=90),
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.APPLY_PARTIAL, result["rejectedClaims"])
        self.assertEqual(control(result)["applied"], 180)
        self.assertEqual(control(result)["candidateApplied"], 90)
        self.assertIn("p131-manual-controls", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_record_and_stop_stay_enabled(self):
        for flag in ("record_enabled", "stop_enabled"):
            result = assess(proposed_with(**{flag: False}))
            self.assertEqual(result["decision"], "rejected", flag)
            self.assertIn(_MODULE.RECORD_OR_STOP_DISABLED, result["rejectedClaims"])
            self.assertTrue(control(result)["record_enabled"])
            self.assertTrue(control(result)["stop_enabled"])
            self.assertEqual(control(result)["applied"], 180)

    def test_source_change_is_rejected_and_the_configuration_is_preserved(self):
        result = assess(
            document(
                proposed=_MODULE.held_proposal(draft="90", submitted=True, applied=90, source_configuration="imax-70mm")
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.SOURCE_CONFIGURATION_CHANGED, result["rejectedClaims"])
        record = control(result)
        self.assertEqual(record["source_configuration"], "1080p-sdr")
        self.assertEqual(record["applied"], 180)
        self.assertEqual(record["candidateApplied"], 90)

    def test_observed_sensor_result_is_not_rewritten_by_the_draft(self):
        committed = _MODULE.make_control(observed=171)
        proposed = _MODULE.held_proposal(observed=90, draft="90", submitted=True, applied=90)
        result = assess(document(committed=committed, proposed=proposed))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.OBSERVED_REWRITTEN, result["rejectedClaims"])
        self.assertEqual(control(result)["observed"], 171)
        self.assertEqual(control(result)["applied"], 180)
        held = assess(document(committed=committed, proposed=_MODULE.held_proposal(observed=171)))
        self.assertEqual(held["decision"], "recorded")
        self.assertEqual(control(held)["observed"], 171)
        self.assertEqual(control(held)["applied"], 180)
        self.assertEqual(control(held)["draft"], "1.")

    def test_reset_restores_the_advertised_value_and_ignores_a_partial_draft(self):
        committed = _MODULE.make_control(applied=90, draft="90")
        proposed = _MODULE.make_control(applied=180, draft="1.", reset=True, orientation="landscape")
        result = assess(document(committed=committed, proposed=proposed))
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        record = control(result)
        self.assertEqual(record["applied"], 180)
        self.assertEqual(record["previousApplied"], 90)
        self.assertEqual(record["draft"], "1.")
        self.assertEqual(record["draftStatus"], "reset")
        self.assertTrue(record["record_enabled"])
        missed = assess(document(committed=committed, proposed=_MODULE.make_control(applied=90, draft="", reset=True)))
        self.assertEqual(missed["decision"], "rejected")
        self.assertIn(_MODULE.RESET_MISSED, missed["rejectedClaims"])
        self.assertEqual(control(missed)["applied"], 90)
        self.assertEqual(control(missed)["candidateApplied"], 180)

    def test_unavailable_controls_need_a_reason_and_do_not_apply(self):
        missing = assess(proposed_with(unavailable=True, unavailable_reason=None, draft="90", submitted=True))
        self.assertEqual(missing["decision"], "rejected")
        self.assertIn(_MODULE.UNAVAILABLE_WITHOUT_REASON, missing["rejectedClaims"])
        self.assertEqual(control(missing)["applied"], 180)
        held = assess(
            proposed_with(
                unavailable=True,
                unavailable_reason="lens does not support this shutter",
                draft="90",
                submitted=True,
                applied=180,
            )
        )
        self.assertEqual(held["decision"], "recorded")
        self.assertEqual(control(held)["applied"], 180)
        self.assertEqual(control(held)["draftStatus"], "unavailable")
        moved = assess(
            proposed_with(
                unavailable=True,
                unavailable_reason="lens does not support this shutter",
                draft="90",
                submitted=True,
                applied=90,
            )
        )
        self.assertEqual(moved["decision"], "rejected")
        self.assertIn(_MODULE.UNAVAILABLE_APPLIED, moved["rejectedClaims"])
        self.assertEqual(control(moved)["applied"], 180)

    def test_a_partial_draft_that_reaches_the_camera_is_rejected(self):
        result = assess(proposed_with(draft="", applied=1))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.PARTIAL_REACHED, result["rejectedClaims"])
        self.assertEqual(control(result)["applied"], 180)
        self.assertIn("p131-manual-controls", result["preservedResults"])

    def test_changed_evidence_id_is_preserved(self):
        result = assess(document(evidenceId="p131-returned-landscape"))
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("p131-returned-landscape", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(control(result)["applied"], 180)
        self.assertEqual(control(result)["draft"], "1.")

    def test_invalid_payloads_raise(self):
        invalid = [
            {},
            [],
            document(schemaVersion=2),
            document(phase="P130"),
            document(implementationBaseRevision="deadbeef"),
            document(applyMutant="no"),
            document(extra=True),
            proposed_with(draft=1),
            proposed_with(applied=True),
            proposed_with(applied=float("nan")),
            proposed_with(minimum=10, maximum=1),
            proposed_with(reset=True, submitted=True),
            proposed_with(orientation="sideways"),
            proposed_with(unit=""),
            document(committed=_MODULE.make_control(applied=900)),
            proposed_with(unavailable_reason="  missing trim  "),
        ]
        for index, payload in enumerate(invalid):
            with self.subTest(index=index):
                with self.assertRaises(ValueError):
                    assess(payload)

    def test_handoff_and_note_keep_the_non_claims(self):
        handoff = json.loads((_ROOT / "docs" / "evidence" / "P131-handoff.json").read_text())
        self.assertEqual(handoff["phase"], "P131")
        self.assertEqual(handoff["nextPhase"], "P132")
        self.assertIsNone(handoff["commit"])
        self.assertEqual(handoff["failures"], 0)
        self.assertEqual(
            handoff["nonClaims"],
            "Host reference only. Not a physical S23 qualification.",
        )
        self.assertEqual(
            handoff["testsRun"],
            "python3 -m unittest discover -s scripts/tests -p 'test_p131*.py' -v",
        )
        for relative in handoff["changedFiles"]:
            self.assertTrue((_ROOT / relative).is_file(), relative)
        note = (_ROOT / "docs" / "P131_DESIGN_MANUAL_CONTROLS_FOR_DELIBERATE_OPERATION.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Manual interaction contract and draft-state tests", note)
        self.assertIn("not a physical S23 measurement", note)
        self.assertIn("sensor-derived Log", note)
        self.assertIn("ten-bit fidelity", note)
        self.assertIn("film-stock fidelity", note)
        self.assertIn("cinema-camera equivalence", note)
        self.assertIn("apply_partial", note)
        self.assertIn("1.", note)

    def test_case_modules_reject_invalid_payloads(self):
        for index in range(1, 9):
            path = Path(__file__).resolve().parents[1] / "gates" / f"p131_tc0{index}.py"
            spec = importlib.util.spec_from_file_location(f"p131_tc0{index}_loaded", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.assertEqual(module.CASE["id"], f"TC-P131-0{index}")
            self.assertEqual(module.CASE["phase"], "P131")
            self.assertEqual(module.CASE["workstream"], 17)
            self.assertRegex(module.NEGATIVE_TOKEN, r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
            with self.assertRaises(ValueError):
                module.evaluate({})
