"""Host checks for the P022 monitoring branch. Not a physical S23 probe.

TC-P022-01..08 are specified elsewhere and are not executed by this module.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "gates"))

from p022_protect_preview_independence import (  # noqa: E402
    BASE_REVISION,
    FIXTURE,
    METHOD,
    MUTANT,
    ORACLE,
    aid_toggle_hashes,
    assess_independence,
    reuses_preview_framebuffer,
    validate_fixture,
)


CLEAN = "1111111111111111111111111111111111111111"
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
HANDOFF_KEYS = (
    "phase",
    "caseIds",
    "changedFiles",
    "commit",
    "testsRun",
    "failures",
    "unverified",
    "nextPhase",
)


def load_fixture() -> dict:
    path = ROOT / "docs" / "P022_PROTECT_PREVIEW_INDEPENDENCE.json"
    return json.loads(path.read_text(encoding="utf-8"))


def load_handoff() -> dict:
    path = ROOT / "docs" / "evidence" / "P022-handoff.json"
    return json.loads(path.read_text(encoding="utf-8"))


class P022PreviewIndependenceTests(unittest.TestCase):
    def test_fixture_encodes_method_oracle_and_base_revision(self) -> None:
        raw = load_fixture()
        self.assertIsNone(validate_fixture(raw))
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P022")
        self.assertEqual(raw["contractId"], "s23-preview-independence-fixture")
        self.assertEqual(raw["implementationBaseRevision"], BASE_REVISION)
        self.assertEqual(raw["normalizationPoint"], "source-normalization")
        self.assertEqual(raw["method"], METHOD)
        self.assertEqual(raw["fixture"], FIXTURE)
        self.assertEqual(raw["oracle"], ORACLE)
        self.assertEqual(raw["mutant"], MUTANT)
        self.assertIn("false-color", raw["fixture"])
        self.assertIn("histogram", raw["fixture"])
        self.assertIn("virtual-film", raw["fixture"])
        self.assertEqual(raw["monitoring"]["downsample"], "160x90")
        self.assertEqual(raw["monitoring"]["displayTransform"], "display-preview")
        self.assertEqual(raw["monitoring"]["freshnessMaxMs"], 750)
        self.assertEqual(
            raw["monitoring"]["overlaySet"],
            ["false-color", "histogram", "virtual-film"],
        )

    def test_aids_enabled_and_disabled_share_the_clean_master(self) -> None:
        raw = load_fixture()
        compared = aid_toggle_hashes(raw)
        self.assertGreaterEqual(len(compared["enabled"]), 2)
        self.assertGreaterEqual(len(compared["disabled"]), 2)
        self.assertEqual(set(compared["enabled"]), {CLEAN})
        self.assertEqual(set(compared["disabled"]), {CLEAN})
        overlay_names = []
        for sample in raw["samples"]:
            self.assertEqual(sample["sourceHash"], CLEAN)
            self.assertEqual(sample["recordedHash"], CLEAN)
            self.assertEqual(sample["recordedFrom"], "clean-master")
            self.assertNotEqual(sample["previewFramebufferHash"], sample["recordedHash"])
            self.assertFalse(reuses_preview_framebuffer(sample))
            overlay_names.extend(sample["overlays"])
        self.assertIn("false-color", overlay_names)
        self.assertIn("histogram", overlay_names)
        self.assertIn("virtual-film", overlay_names)
        result = assess_independence(raw)
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], "P022")
        self.assertEqual(result["decision"], "invariant")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"], [CLEAN, "synthetic-capture-p022"])
        self.assertIn(CLEAN, result["preservedResults"])
        self.assertTrue(any("enabled and disabled" in item for item in result["reasons"]))
        self.assertTrue(any("monitoring" in item for item in result["reasons"]))
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))

    def test_mutant_preview_framebuffer_is_rejected(self) -> None:
        raw = load_fixture()
        mutant = copy.deepcopy(raw)
        for sample in mutant["samples"]:
            sample["recordedFrom"] = "preview-framebuffer"
            sample["recordedHash"] = sample["previewFramebufferHash"]
        self.assertTrue(any(reuses_preview_framebuffer(sample) for sample in mutant["samples"]))
        result = assess_independence(mutant)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "invariant"})
        self.assertIn("composited-preview-as-recording-source", result["rejectedClaims"])
        self.assertIn("clean-master-drift", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][0], CLEAN)
        self.assertIn("synthetic-capture-p022", result["preservedResults"])
        self.assertTrue(result["reasons"])
        honest = assess_independence(raw)
        self.assertEqual(honest["decision"], "invariant")
        self.assertNotEqual(result["decision"], honest["decision"])

    def test_one_reused_framebuffer_still_rejects_and_keeps_the_master(self) -> None:
        raw = load_fixture()
        mutant = copy.deepcopy(raw)
        mutant["samples"][1]["recordedHash"] = mutant["samples"][1]["previewFramebufferHash"]
        self.assertTrue(reuses_preview_framebuffer(mutant["samples"][1]))
        self.assertFalse(reuses_preview_framebuffer(mutant["samples"][0]))
        result = assess_independence(mutant)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(
            result["rejectedClaims"],
            ["composited-preview-as-recording-source", "clean-master-drift"],
        )
        self.assertIn(CLEAN, result["preservedResults"])
        self.assertIn(raw["sequenceId"], result["preservedResults"])

    def test_hash_only_reuse_is_the_mutant_even_if_the_label_says_clean(self) -> None:
        raw = load_fixture()
        mutant = copy.deepcopy(raw)
        mutant["samples"][3]["recordedFrom"] = "clean-master"
        mutant["samples"][3]["recordedHash"] = mutant["samples"][3]["previewFramebufferHash"]
        result = assess_independence(mutant)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("composited-preview-as-recording-source", result["rejectedClaims"])
        self.assertNotIn(result["decision"], {"invariant", "qualified", "allowed"})

    def test_incomplete_aid_toggle_is_withheld(self) -> None:
        raw = load_fixture()
        only_on = copy.deepcopy(raw)
        only_on["samples"] = [sample for sample in only_on["samples"] if sample["aidsEnabled"]]
        for index, sample in enumerate(only_on["samples"]):
            sample["index"] = index
        result = assess_independence(only_on)
        self.assertEqual(result["decision"], "withheld")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "invariant"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn(CLEAN, result["preservedResults"])
        self.assertTrue(any("incomplete" in item for item in result["reasons"]))

    def test_clean_master_drift_without_the_preview_buffer_is_rejected(self) -> None:
        raw = load_fixture()
        drifted = copy.deepcopy(raw)
        drifted["samples"][0]["sourceHash"] = "9999999999999999999999999999999999999999"
        drifted["samples"][0]["recordedHash"] = "9999999999999999999999999999999999999999"
        drifted["samples"][0]["previewFramebufferHash"] = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        result = assess_independence(drifted)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["clean-master-drift"])
        self.assertNotIn("composited-preview-as-recording-source", result["rejectedClaims"])
        self.assertIn(CLEAN, result["preservedResults"])
        self.assertIn("9999999999999999999999999999999999999999", result["preservedResults"])

    def test_invalid_fixtures_raise(self) -> None:
        valid = load_fixture()
        extra = copy.deepcopy(valid)
        extra["note"] = "device probe"
        missing = copy.deepcopy(valid)
        del missing["mutant"]
        wrong_phase = copy.deepcopy(valid)
        wrong_phase["phase"] = "P021"
        wrong_revision = copy.deepcopy(valid)
        wrong_revision["implementationBaseRevision"] = "fffd5c9a63cb732e103052acae29ae0c251585cc"
        wrong_method = copy.deepcopy(valid)
        wrong_method["method"] = "reuse the preview"
        empty = copy.deepcopy(valid)
        empty["samples"] = []
        bad_hash = copy.deepcopy(valid)
        bad_hash["cleanMasterHash"] = "1111"
        burned = copy.deepcopy(valid)
        burned["samples"][0]["aidsEnabled"] = True
        burned["samples"][0]["overlays"] = []
        stale = copy.deepcopy(valid)
        stale["samples"][0]["freshnessMs"] = 751
        duplicate = copy.deepcopy(valid)
        duplicate["samples"][4]["overlays"] = ["histogram", "histogram"]
        cases = (
            None,
            [],
            {},
            extra,
            missing,
            wrong_phase,
            wrong_revision,
            wrong_method,
            empty,
            bad_hash,
            burned,
            stale,
            duplicate,
        )
        for sample in cases:
            with self.subTest(sample=type(sample).__name__):
                with self.assertRaises(ValueError):
                    validate_fixture(sample)

    def test_handoff_lists_cases_and_does_not_invent_a_commit(self) -> None:
        handoff = load_handoff()
        self.assertEqual(tuple(handoff), HANDOFF_KEYS)
        self.assertEqual(handoff["phase"], "P022")
        self.assertEqual(
            handoff["caseIds"],
            [f"TC-P022-0{index}" for index in range(1, 9)],
        )
        self.assertIsNone(handoff["commit"])
        self.assertEqual(handoff["failures"], [])
        self.assertEqual(handoff["nextPhase"], "P023")
        self.assertIn(
            "python3 -m unittest discover -s scripts/tests -p 'test_p022*.py' -v",
            handoff["testsRun"],
        )
        self.assertIn("physical S23 capture", handoff["unverified"])
        self.assertIn("cinema-camera equivalence", handoff["unverified"])
        for relative in handoff["changedFiles"]:
            self.assertTrue((ROOT / relative).is_file(), relative)


if __name__ == "__main__":
    unittest.main()
