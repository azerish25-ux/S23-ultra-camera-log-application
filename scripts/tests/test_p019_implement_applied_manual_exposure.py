"""Host checks for the P019 applied manual exposure fixture. Not a physical S23 probe.

TC-P019-01..08 are specified elsewhere and are not executed by this module.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "gates"))

from p008_protocol import validate_handoff
from p019_implement_applied_manual_exposure import (
    BASE_REVISION,
    CONFIRMED_CLAIM,
    FIXTURE,
    FIXTURE_ID,
    METHOD,
    MUTANT,
    MUTANT_CLAIM,
    ORACLE,
    REQUIRED_LOCK,
    assess,
    effective_target,
    validate_fixture,
)


RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def load_fixture() -> dict:
    path = ROOT / "docs" / "P019_IMPLEMENT_APPLIED_MANUAL_EXPOSURE.json"
    return json.loads(path.read_text(encoding="utf-8"))


def load_handoff() -> dict:
    path = ROOT / "docs" / "evidence" / "P019-handoff.json"
    return json.loads(path.read_text(encoding="utf-8"))


class P019AppliedManualExposureTests(unittest.TestCase):
    def test_fixture_encodes_method_fixture_oracle_and_mutant(self) -> None:
        raw = load_fixture()
        self.assertIsNone(validate_fixture(raw))
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P019")
        self.assertEqual(raw["fixtureId"], FIXTURE_ID)
        self.assertEqual(raw["implementationBaseRevision"], BASE_REVISION)
        self.assertEqual(raw["method"], METHOD)
        self.assertEqual(raw["fixture"], FIXTURE)
        self.assertEqual(raw["oracle"], ORACLE)
        self.assertEqual(raw["mutant"], MUTANT)
        self.assertEqual(raw["lock"]["required"], REQUIRED_LOCK)
        self.assertEqual(raw["lock"]["observed"], REQUIRED_LOCK)
        self.assertEqual(raw["presentation"], "observed")
        self.assertGreater(raw["request"]["shutterNs"], raw["request"]["framePeriodNs"])
        self.assertEqual(raw["result"]["iso"], raw["result"]["previousAutomaticIso"])
        self.assertNotEqual(raw["result"]["iso"], raw["request"]["iso"])
        self.assertEqual(raw["request"]["aeMode"], "off")
        self.assertEqual(raw["tolerances"]["isoFraction"], 0.05)
        target = effective_target(raw["request"], raw["sensorLimits"])
        self.assertTrue(target["visible"])
        self.assertTrue(target["shutterClampedToFrame"])
        self.assertFalse(target["isoClamped"])
        self.assertEqual(target["iso"], 800)
        self.assertEqual(target["shutterNs"], raw["request"]["framePeriodNs"])

    def test_fixture_withholds_confirmed_control_and_keeps_the_mismatch(self) -> None:
        raw = load_fixture()
        result = assess(raw)
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], "P019")
        self.assertEqual(result["decision"], "withheld")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [CONFIRMED_CLAIM])
        self.assertIn("observed-iso:100", result["preservedResults"])
        self.assertIn("requested-iso:800", result["preservedResults"])
        self.assertNotIn("observed-iso:800", result["preservedResults"])
        self.assertIn("effective-iso:800", result["preservedResults"])
        self.assertIn("effective-shutter-ns:33333333", result["preservedResults"])
        self.assertIn("requested-shutter-ns:50000000", result["preservedResults"])
        self.assertIn("iso-status:measured_mismatch", result["preservedResults"])
        self.assertIn("previous-automatic-iso:100", result["preservedResults"])
        self.assertIn("effective-target-visible", result["preservedResults"])
        self.assertTrue(any("user-visible effective target" in item for item in result["reasons"]))
        self.assertTrue(any("longer than frame period" in item for item in result["reasons"]))
        self.assertIn("iso measured mismatch", result["reasons"])
        self.assertNotIn("iso missing metadata", result["reasons"])
        self.assertTrue(any("previous automatic 100" in item for item in result["reasons"]))
        self.assertTrue(any("cannot claim confirmed manual control" in item for item in result["reasons"]))
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))

    def test_mutant_does_not_show_requested_iso_as_observed(self) -> None:
        """Fails if requested ISO is copied into the observed sensor value."""
        raw = load_fixture()
        honest = assess(raw)
        self.assertIn("observed-iso:100", honest["preservedResults"])
        self.assertNotIn("observed-iso:800", honest["preservedResults"])
        mutant = copy.deepcopy(raw)
        mutant["presentation"] = "requested_as_observed"
        refused = assess(mutant)
        self.assertEqual(refused["decision"], "rejected")
        self.assertNotIn(refused["decision"], {"qualified", "allowed", "result_matched"})
        self.assertEqual(refused["rejectedClaims"], [MUTANT_CLAIM, CONFIRMED_CLAIM])
        self.assertIn(MUTANT, refused["reasons"])
        self.assertTrue(any("was not copied" in item for item in refused["reasons"]))
        self.assertEqual(refused["preservedResults"], honest["preservedResults"])
        self.assertIn("observed-iso:100", refused["preservedResults"])
        self.assertNotIn("observed-iso:800", refused["preservedResults"])
        self.assertIn("iso-status:measured_mismatch", refused["preservedResults"])

    def test_missing_metadata_is_not_rewritten_as_a_measured_mismatch(self) -> None:
        raw = load_fixture()
        missing = copy.deepcopy(raw)
        missing["result"]["iso"] = None
        missing["result"]["metadata"]["iso"] = "missing"
        result = assess(missing)
        self.assertEqual(result["decision"], "withheld")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("iso missing metadata", result["reasons"])
        self.assertNotIn("iso measured mismatch", result["reasons"])
        self.assertIn("iso-status:missing_metadata", result["preservedResults"])
        self.assertIn("observed-iso:missing", result["preservedResults"])
        self.assertNotIn("observed-iso:800", result["preservedResults"])
        self.assertIn("effective-target-visible", result["preservedResults"])
        self.assertIn(CONFIRMED_CLAIM, result["rejectedClaims"])

    def test_present_shutter_disagreement_is_a_measured_mismatch(self) -> None:
        raw = load_fixture()
        disagreed = copy.deepcopy(raw)
        disagreed["result"]["shutterNs"] = 10000000
        result = assess(disagreed)
        self.assertEqual(result["decision"], "withheld")
        self.assertIn("shutter measured mismatch", result["reasons"])
        self.assertNotIn("shutter missing metadata", result["reasons"])
        self.assertIn("shutter-status:measured_mismatch", result["preservedResults"])
        self.assertIn("observed-shutter-ns:10000000", result["preservedResults"])
        self.assertIn("effective-shutter-ns:33333333", result["preservedResults"])

    def test_lock_and_auto_exposure_block_a_numeric_match(self) -> None:
        raw = load_fixture()
        matched = copy.deepcopy(raw)
        matched["request"]["iso"] = 100
        matched["request"]["shutterNs"] = 33333333
        matched["result"]["iso"] = 100
        ready = assess(matched)
        self.assertEqual(ready["decision"], "result_matched")
        self.assertNotIn(ready["decision"], {"qualified", "allowed"})
        self.assertIn(CONFIRMED_CLAIM, ready["rejectedClaims"])
        self.assertIn("host arithmetic matched the visible effective target", ready["reasons"])
        unlocked = copy.deepcopy(matched)
        unlocked["lock"]["observed"] = "manual_exposure_pending"
        waiting = assess(unlocked)
        self.assertEqual(waiting["decision"], "withheld")
        self.assertTrue(any("lock transition has not completed" in item for item in waiting["reasons"]))
        self.assertIn("manual exposure lock transition is still open", waiting["openQuestions"])
        auto = copy.deepcopy(matched)
        auto["request"]["aeMode"] = "on"
        still_auto = assess(auto)
        self.assertEqual(still_auto["decision"], "withheld")
        self.assertIn("auto exposure is still active", still_auto["reasons"])
        self.assertIn(CONFIRMED_CLAIM, still_auto["rejectedClaims"])

    def test_iso_above_the_sensor_limit_is_clamped_only_on_the_visible_target(self) -> None:
        raw = load_fixture()
        clamped = copy.deepcopy(raw)
        clamped["request"]["iso"] = 6400
        clamped["request"]["shutterNs"] = 33333333
        clamped["result"]["iso"] = 3200
        target = effective_target(clamped["request"], clamped["sensorLimits"])
        self.assertEqual(target["iso"], 3200)
        self.assertTrue(target["isoClamped"])
        self.assertTrue(target["visible"])
        result = assess(clamped)
        self.assertEqual(result["decision"], "result_matched")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("effective-iso:3200", result["preservedResults"])
        self.assertIn("requested-iso:6400", result["preservedResults"])
        self.assertIn("observed-iso:3200", result["preservedResults"])
        self.assertNotIn("observed-iso:6400", result["preservedResults"])
        self.assertTrue(any("clamped to visible effective iso 3200" in item for item in result["reasons"]))
        self.assertIn(CONFIRMED_CLAIM, result["rejectedClaims"])

    def test_handoff_is_blocked_without_a_commit(self) -> None:
        handoff = load_handoff()
        self.assertIsNone(validate_handoff(handoff))
        self.assertEqual(handoff["phase"], "P019")
        self.assertIsNone(handoff["commit"])
        self.assertEqual(handoff["nextPhase"], "blocked")
        self.assertEqual(handoff["failures"], [])
        self.assertEqual(len(handoff["caseIds"]), 8)
        self.assertIn("physical S23 qualification", handoff["unverified"])
        self.assertTrue(handoff["testsRun"])
        self.assertIn(
            "python3 -m unittest discover -s scripts/tests -p 'test_p019*.py' -v",
            handoff["testsRun"],
        )

    def test_invalid_fixtures_raise(self) -> None:
        valid = load_fixture()
        extra = copy.deepcopy(valid)
        extra["note"] = "device probe"
        missing = copy.deepcopy(valid)
        del missing["presentation"]
        bad_phase = copy.deepcopy(valid)
        bad_phase["phase"] = "P018"
        bad_revision = copy.deepcopy(valid)
        bad_revision["implementationBaseRevision"] = "abc"
        mutant_text = copy.deepcopy(valid)
        mutant_text["mutant"] = "treat the request as the sensor"
        requested_observed = copy.deepcopy(valid)
        requested_observed["presentation"] = "observed_as_requested"
        missing_number = copy.deepcopy(valid)
        missing_number["result"]["iso"] = None
        bool_iso = copy.deepcopy(valid)
        bool_iso["request"]["iso"] = True
        short_frame = copy.deepcopy(valid)
        short_frame["sensorLimits"]["shutterMinNs"] = 40000000
        ae = copy.deepcopy(valid)
        ae["request"]["aeMode"] = "manual"
        lock = copy.deepcopy(valid)
        lock["lock"]["required"] = "ae_locked"
        cases = (
            None,
            [],
            {},
            extra,
            missing,
            bad_phase,
            bad_revision,
            mutant_text,
            requested_observed,
            missing_number,
            bool_iso,
            short_frame,
            ae,
            lock,
        )
        for sample in cases:
            with self.subTest(sample=type(sample).__name__):
                with self.assertRaises(ValueError):
                    validate_fixture(sample)


if __name__ == "__main__":
    unittest.main()
