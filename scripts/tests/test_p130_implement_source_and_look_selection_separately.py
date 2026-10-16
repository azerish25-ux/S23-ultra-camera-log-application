"""Host checks for P130. Not a physical S23 probe."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "p130_implement_source_and_look_selection_separately",
    Path(__file__).resolve().parents[1]
    / "gates"
    / "p130_implement_source_and_look_selection_separately.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
assess = _MODULE.assess

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def load_document() -> dict:
    return json.loads(
        (
            _ROOT / "docs" / "P130_IMPLEMENT_SOURCE_AND_LOOK_SELECTION_SEPARATELY.json"
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


def isolation(result):
    return result["preservedResults"][1]


class P130Tests(unittest.TestCase):
    def test_phase_constants_match_the_spec(self):
        self.assertEqual(_MODULE.BASE_REVISION, "3fbad4bc0e0336e273d2723ec873f001e8865323")
        self.assertEqual(_MODULE.PHASE, "P130")
        self.assertEqual(_MODULE.WORKSTREAM, 17)
        self.assertEqual(_MODULE.TITLE, "Implement source and look selection separately")
        self.assertEqual(
            _MODULE.GOAL,
            "Prevent users from confusing capture capability with a virtual film format.",
        )
        self.assertEqual(
            _MODULE.METHOD,
            "Use distinct selectors for physical source mode, virtual format, stock, lens interpretation, "
            "and finishing recipe. Show computational cost and calibration status where relevant. "
            "Changing a look must not silently alter recording resolution or source lineage.",
        )
        self.assertEqual(
            _MODULE.FIXTURE,
            "Selecting an IMAX-style recipe while the active source is a qualified 1080p SDR mode.",
        )
        self.assertEqual(
            _MODULE.ORACLE,
            "The interface preserves and displays the source mode while labelling the large-format "
            "appearance as simulated.",
        )
        self.assertEqual(
            _MODULE.MUTANT,
            "Rename the active recording mode IMAX 70mm after a preset selection.",
        )
        self.assertEqual(_MODULE.DELIVERABLE, "Separated control model and truthfulness UI tests")
        self.assertEqual(_MODULE.DEPENDENCIES, ("P129",))

    def test_fixture_records_imax_look_without_touching_source(self):
        source = load_document()
        result = assess(source)
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "P130")
        self.assertEqual(result["decision"], "recorded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn(source["evidenceId"], result["preservedResults"])
        self.assertIn(source["claim"], result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn(_MODULE.ORACLE, " ".join(result["reasons"]))
        self.assertIn(
            "look change isolated: source_id, source_sha256, and source_transfer unchanged",
            result["reasons"],
        )
        record = isolation(result)
        self.assertEqual(record["source_id"], "qualified-1080p-sdr")
        self.assertEqual(record["source_sha256"], _MODULE.FIXTURE_SOURCE_SHA256)
        self.assertEqual(record["source_transfer"], "bt709")
        self.assertEqual(record["look_id"], "imax-style-simulated")
        self.assertTrue(record["look_params"]["simulated"])
        self.assertTrue(record["source_retained"])
        self.assertEqual(record["recording_mode"], "1080p SDR")
        self.assertEqual(record["changedSourceFields"], [])
        self.assertTrue(record["lookChanged"])
        self.assertIn("computationalCost=preview-only", result["reasons"])
        self.assertIn("calibrationStatus=not-qualified", result["reasons"])

    def test_look_param_edit_keeps_source_sha(self):
        committed = _MODULE.make_selection()
        proposed = _MODULE.make_selection(look_params={"contrast": 1.4, "stock": "print"})
        result = assess(document(committed=committed, proposed=proposed))
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        record = isolation(result)
        self.assertEqual(record["source_sha256"], committed["source_sha256"])
        self.assertEqual(record["source_id"], committed["source_id"])
        self.assertEqual(record["source_transfer"], "bt709")
        self.assertEqual(record["changedSourceFields"], [])

    def test_look_change_that_alters_source_is_rejected_and_source_is_kept(self):
        result = assess(proposed_with(source_sha256="ab" * 32, source_id="imax-70mm"))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.LOOK_ALTERED_SOURCE, result["rejectedClaims"])
        record = isolation(result)
        self.assertEqual(record["source_id"], "qualified-1080p-sdr")
        self.assertEqual(record["source_sha256"], _MODULE.FIXTURE_SOURCE_SHA256)
        self.assertEqual(record["source_transfer"], "bt709")
        self.assertEqual(record["changedSourceFields"], ["source_id", "source_sha256"])
        self.assertIn("p130-source-look", result["preservedResults"])

    def test_log_look_does_not_rewrite_transfer(self):
        proposed = _MODULE.make_selection(
            look_id="LogC3-emulation",
            look_params={"print": "sim", "simulated": False},
        )
        result = assess(document(proposed=proposed))
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(isolation(result)["source_transfer"], "bt709")
        self.assertEqual(isolation(result)["look_id"], "LogC3-emulation")
        self.assertNotIn(_MODULE.LOOK_REWROTE_TRANSFER, result["rejectedClaims"])

    def test_logc3_relabel_of_bt709_and_hlg_is_rejected(self):
        for original in ("bt709", "HLG", "BT.709"):
            proposed = _MODULE.make_selection(
                source_transfer="logc3",
                look_id="LogC3",
                look_params={"curve": "log"},
            )
            committed = _MODULE.make_selection(source_transfer=original)
            result = assess(document(committed=committed, proposed=proposed))
            self.assertEqual(result["decision"], "rejected", original)
            self.assertIn(_MODULE.LOOK_RELABELLED_LOGC3, result["rejectedClaims"])
            self.assertIn(_MODULE.LOOK_REWROTE_TRANSFER, result["rejectedClaims"])
            self.assertIn(_MODULE.LOOK_ALTERED_SOURCE, result["rejectedClaims"])
            self.assertEqual(isolation(result)["source_transfer"], original)
            self.assertIn("p130-source-look", result["preservedResults"])

    def test_look_params_cannot_smuggle_logc3(self):
        proposed = _MODULE.imax_proposal(
            look_params={
                "appearance": "large-format",
                "simulated": True,
                "source_transfer": "LogC3",
            }
        )
        result = assess(document(proposed=proposed))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.LOOK_PARAMS_ALTER_SOURCE, result["rejectedClaims"])
        self.assertIn(_MODULE.LOOK_RELABELLED_LOGC3, result["rejectedClaims"])
        self.assertEqual(isolation(result)["source_transfer"], "bt709")

    def test_transfer_alias_is_not_a_source_change(self):
        proposed = _MODULE.imax_proposal(source_transfer="BT.709")
        result = assess(document(proposed=proposed))
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(isolation(result)["changedSourceFields"], [])
        self.assertEqual(isolation(result)["source_transfer"], "bt709")

    def test_sha_case_difference_is_not_a_source_change(self):
        proposed = _MODULE.imax_proposal(source_sha256=_MODULE.FIXTURE_SOURCE_SHA256.upper())
        result = assess(document(proposed=proposed))
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(isolation(result)["changedSourceFields"], [])

    def test_applying_a_look_with_no_source_is_rejected(self):
        proposed = _MODULE.make_selection(
            source_id=None,
            source_sha256=None,
            source_transfer=None,
            look_id="imax-style-simulated",
            look_params={"appearance": "large-format", "simulated": True},
        )
        result = assess(document(proposed=proposed))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.LOOK_APPLIED_WITHOUT_SOURCE, result["rejectedClaims"])
        self.assertIn("p130-source-look", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_clearing_the_look_keeps_the_source(self):
        proposed = _MODULE.make_selection(look_id=None, look_params=None, source_retained=True)
        result = assess(document(proposed=proposed))
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        record = isolation(result)
        self.assertIsNone(record["look_id"])
        self.assertTrue(record["source_retained"])
        self.assertEqual(record["source_sha256"], _MODULE.FIXTURE_SOURCE_SHA256)
        self.assertEqual(record["source_id"], "qualified-1080p-sdr")
        self.assertEqual(record["source_transfer"], "bt709")
        self.assertIn("look cleared; source bytes retained", result["reasons"])
        self.assertIn("source_retained=true", result["reasons"])

    def test_clearing_the_look_must_not_delete_source_bytes(self):
        proposed = _MODULE.make_selection(look_id=None, look_params=None, source_retained=False)
        result = assess(document(proposed=proposed))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.SOURCE_NOT_RETAINED, result["rejectedClaims"])
        record = isolation(result)
        self.assertEqual(record["source_sha256"], _MODULE.FIXTURE_SOURCE_SHA256)
        self.assertFalse(record["source_retained"])
        self.assertIn("p130-source-look", result["preservedResults"])

    def test_source_only_transfer_edit_is_not_blamed_on_an_unchanged_look(self):
        proposed = _MODULE.make_selection(source_transfer="hlg")
        result = assess(document(proposed=proposed))
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(isolation(result)["changedSourceFields"], ["source_transfer"])
        self.assertFalse(isolation(result)["lookChanged"])
        self.assertNotIn(_MODULE.LOOK_RELABELLED_LOGC3, result["rejectedClaims"])

    def test_imax_mode_rename_and_mutant_flag_are_rejected(self):
        renamed = assess(proposed_with(recording_mode="IMAX 70mm"))
        self.assertEqual(renamed["decision"], "rejected")
        self.assertIn(_MODULE.RENAMED_IMAX_70MM, renamed["rejectedClaims"])
        self.assertIn(_MODULE.MUTANT, renamed["reasons"])
        self.assertEqual(isolation(renamed)["recording_mode"], "1080p SDR")
        self.assertEqual(isolation(renamed)["source_transfer"], "bt709")
        flagged = assess(document(applyMutant=True))
        self.assertEqual(flagged["decision"], "rejected")
        self.assertIn(_MODULE.RENAMED_IMAX_70MM, flagged["rejectedClaims"])
        self.assertIn("p130-source-look", flagged["preservedResults"])
        self.assertNotIn(flagged["decision"], {"qualified", "allowed"})

    def test_large_format_look_must_be_labelled_simulated(self):
        proposed = _MODULE.imax_proposal(look_params={"appearance": "large-format", "simulated": False})
        result = assess(document(proposed=proposed))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.LARGE_FORMAT_UNLABELLED, result["rejectedClaims"])

    def test_invalid_payloads_raise(self):
        invalid = [
            {},
            [],
            document(schemaVersion=2),
            document(phase="P131"),
            document(implementationBaseRevision="deadbeef"),
            document(applyMutant="no"),
            document(extra=True),
            proposed_with(source_sha256="not-a-digest"),
            proposed_with(look_params=["not", "an", "object"]),
            proposed_with(source_retained="yes"),
            proposed_with(look_params={"gain": float("nan")}),
        ]
        for index, payload in enumerate(invalid):
            with self.subTest(index=index):
                with self.assertRaises(ValueError):
                    assess(payload)

    def test_handoff_and_note_keep_the_non_claims(self):
        handoff = json.loads((_ROOT / "docs" / "evidence" / "P130-handoff.json").read_text())
        self.assertEqual(handoff["phase"], "P130")
        self.assertEqual(handoff["nextPhase"], "P131")
        self.assertIsNone(handoff["commit"])
        self.assertEqual(handoff["failures"], 0)
        self.assertEqual(
            handoff["nonClaims"],
            "Host reference only. Not a physical S23 qualification.",
        )
        self.assertEqual(
            handoff["testsRun"],
            "python3 -m unittest discover -s scripts/tests -p 'test_p130*.py' -v",
        )
        note = (_ROOT / "docs" / "P130_IMPLEMENT_SOURCE_AND_LOOK_SELECTION_SEPARATELY.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Separated control model and truthfulness UI tests", note)
        self.assertIn("not a physical S23 measurement", note)
        self.assertIn("sensor-derived Log", note)
        self.assertIn("ten-bit fidelity", note)
        self.assertIn("film-stock fidelity", note)
        self.assertIn("cinema-camera equivalence", note)
        self.assertIn("source_sha256", note)

    def test_case_modules_reject_invalid_payloads(self):
        for index in range(1, 9):
            path = Path(__file__).resolve().parents[1] / "gates" / f"p130_tc0{index}.py"
            spec = importlib.util.spec_from_file_location(f"p130_tc0{index}_loaded", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.assertEqual(module.CASE["id"], f"TC-P130-0{index}")
            self.assertEqual(module.CASE["phase"], "P130")
            self.assertEqual(module.CASE["workstream"], 17)
            with self.assertRaises(ValueError):
                module.evaluate({})
