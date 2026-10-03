"""Host checks for the P063 editor interoperability fixture. Not a physical S23 probe.

TC-P063-01..08 are specified elsewhere and are not executed by this module.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "gates"))

from p063_validate_editor_interoperability import (  # noqa: E402
    BASE_REVISION,
    FIXTURE,
    HOST_LIMIT,
    HONEST,
    MAP_ID,
    METHOD,
    MUTANT,
    MUTANT_MODE,
    ORACLE,
    assess,
    opening_would_approve_interoperability,
    tonal_mismatch,
    validate_document,
)


RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
VIDEO_IMPORT = (
    "import:video:video-levels:video:independent-decoder:1.4.2:manual=true:auto-tested=false"
)
FULL_IMPORT = (
    "import:full:full-range:full:independent-decoder:1.4.2:manual=true:auto-tested=false"
)


def load_document() -> dict:
    path = ROOT / "docs" / "P063_VALIDATE_EDITOR_INTEROPERABILITY.json"
    return json.loads(path.read_text(encoding="utf-8"))


class P063EditorInteroperabilityTests(unittest.TestCase):
    def assert_result(self, result) -> None:
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], "P063")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "interoperable"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) and item for item in result[key]))

    def test_constants_encode_method_fixture_oracle_and_mutant(self) -> None:
        self.assertEqual(MAP_ID, "s23-editor-interoperability-fixture")
        self.assertEqual(BASE_REVISION, "d4deac8fc82832fd23396a01065c5f0bf9da6670")
        self.assertIn("explicit import instructions", METHOD)
        self.assertIn("do not claim automatic recognition without testing it", METHOD)
        self.assertEqual(
            FIXTURE,
            "A LogC3 export imported once at video levels and once with an incorrect "
            "full-range assumption.",
        )
        self.assertEqual(
            ORACLE,
            "The protocol detects the tonal mismatch and documents the correct supported workflow.",
        )
        self.assertEqual(
            MUTANT,
            "Approve interoperability because a generic player opens the file.",
        )
        self.assertEqual(HONEST, "detect-mismatch")
        self.assertEqual(MUTANT_MODE, "player-opens")

    def test_fixture_records_the_tonal_mismatch_and_keeps_both_imports(self) -> None:
        raw = load_document()
        self.assertIsNone(validate_document(raw))
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P063")
        self.assertEqual(raw["mapId"], MAP_ID)
        self.assertEqual(raw["implementationBaseRevision"], BASE_REVISION)
        self.assertEqual(raw["method"], METHOD)
        self.assertEqual(raw["fixture"], FIXTURE)
        self.assertEqual(raw["oracle"], ORACLE)
        self.assertEqual(raw["mutant"], MUTANT)
        self.assertEqual(raw["export"]["encoding"], "LogC3")
        self.assertEqual(raw["export"]["range"], "video")
        self.assertEqual(raw["export"]["primaries"], "AWG3")
        self.assertEqual(raw["videoImport"]["rangeAssumption"], "video")
        self.assertEqual(raw["fullRangeImport"]["rangeAssumption"], "full")
        self.assertTrue(tonal_mismatch(raw))
        self.assertTrue(opening_would_approve_interoperability(raw))
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "mismatch_recorded")
        self.assertEqual(result["rejectedClaims"], ["incorrect-full-range"])
        self.assertIn("export:LogC3:AWG3:LogC3:video:Main10", result["preservedResults"])
        self.assertIn(VIDEO_IMPORT, result["preservedResults"])
        self.assertIn(FULL_IMPORT, result["preservedResults"])
        self.assertIn("sidecar:true:video:AWG3:LogC3:LogC3", result["preservedResults"])
        self.assertIn(
            "consumer:generic-player:unmeasured:opened=true:thumbnail=true:auto-claim=false",
            result["preservedResults"],
        )
        self.assertTrue(any(item.startswith("workflow:video:documented=true:") for item in result["preservedResults"]))
        self.assertIn(ORACLE, result["reasons"])
        self.assertIn(HOST_LIMIT, result["reasons"])
        self.assertNotIn(MUTANT, result["reasons"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "interoperable"})

    def test_mutant_player_open_is_not_interoperability(self) -> None:
        raw = load_document()
        honest = assess(raw)
        mutant = assess(raw, interpretation=MUTANT_MODE)
        self.assert_result(mutant)
        self.assertTrue(opening_would_approve_interoperability(raw))
        self.assertEqual(honest["decision"], "mismatch_recorded")
        self.assertEqual(mutant["decision"], "rejected")
        self.assertEqual(mutant["rejectedClaims"][0], "generic-player-open")
        self.assertIn("incorrect-full-range", mutant["rejectedClaims"])
        self.assertNotIn(mutant["decision"], {"qualified", "allowed", "interoperable", "mismatch_recorded"})
        self.assertIn(MUTANT, mutant["reasons"])
        self.assertIn("mutant interpretation rejected", mutant["openQuestions"])
        self.assertEqual(honest["preservedResults"], mutant["preservedResults"])
        self.assertIn(VIDEO_IMPORT, mutant["preservedResults"])
        self.assertIn(FULL_IMPORT, mutant["preservedResults"])
        self.assertIn("export:LogC3:AWG3:LogC3:video:Main10", mutant["preservedResults"])

    def test_missing_workflow_rejects_and_keeps_the_full_range_import(self) -> None:
        raw = load_document()
        raw["workflow"]["documented"] = False
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("workflow-not-documented", result["rejectedClaims"])
        self.assertIn("incorrect-full-range", result["rejectedClaims"])
        self.assertIn(FULL_IMPORT, result["preservedResults"])
        self.assertIn(VIDEO_IMPORT, result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "mismatch_recorded"})

    def test_aligned_imports_are_withheld_even_if_the_player_opens(self) -> None:
        raw = load_document()
        raw["fullRangeImport"]["rangeAssumption"] = "video"
        self.assertFalse(tonal_mismatch(raw))
        result = assess(raw)
        self.assertEqual(result["decision"], "withheld")
        self.assertNotIn("incorrect-full-range", result["rejectedClaims"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "interoperable", "mismatch_recorded"})
        self.assertTrue(any(item.startswith("import:full:") for item in result["preservedResults"]))
        self.assertIn("file opening is not interoperability", result["openQuestions"])

    def test_untested_automatic_recognition_is_rejected(self) -> None:
        raw = load_document()
        raw["consumer"]["automaticRecognitionClaimed"] = True
        result = assess(raw)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("untested-automatic-recognition", result["rejectedClaims"])
        self.assertIn("incorrect-full-range", result["rejectedClaims"])
        self.assertIn(FULL_IMPORT, result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "interoperable"})

    def test_sidecar_contradiction_keeps_both_descriptors(self) -> None:
        raw = load_document()
        raw["sidecar"]["range"] = "full"
        result = assess(raw)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("sidecar-contradiction", result["rejectedClaims"])
        self.assertIn("sidecar:true:full:AWG3:LogC3:LogC3", result["preservedResults"])
        self.assertIn("export:LogC3:AWG3:LogC3:video:Main10", result["preservedResults"])

    def test_invalid_documents_raise(self) -> None:
        valid = load_document()
        extra = copy.deepcopy(valid)
        extra["note"] = "device probe"
        missing = copy.deepcopy(valid)
        del missing["workflow"]
        bad_phase = copy.deepcopy(valid)
        bad_phase["phase"] = "P062"
        bad_revision = copy.deepcopy(valid)
        bad_revision["implementationBaseRevision"] = "abc"
        bool_opened = copy.deepcopy(valid)
        bool_opened["consumer"]["opened"] = 1
        same_id = copy.deepcopy(valid)
        same_id["fullRangeImport"]["id"] = same_id["videoImport"]["id"]
        cases = (
            None,
            [],
            {},
            extra,
            missing,
            bad_phase,
            bad_revision,
            bool_opened,
            same_id,
        )
        for sample in cases:
            with self.subTest(sample=type(sample).__name__):
                with self.assertRaises(ValueError):
                    validate_document(sample)
        with self.assertRaises(ValueError):
            assess(valid, interpretation="interoperable")


if __name__ == "__main__":
    unittest.main()
