"""P006 risk register and phase-entry decision log."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "gates"))
import p006_register


def proposal_from(decision: dict) -> dict:
    return {key: decision[key] for key in p006_register.PROPOSAL_KEYS}


class P006RegisterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.register = json.loads((ROOT / "docs" / "RISK_REGISTER.json").read_text())
        self.log = json.loads((ROOT / "docs" / "PHASE_ENTRY_LOG.json").read_text())

    def test_shipped_register_and_log_validate(self) -> None:
        p006_register.validate_register(self.register)
        p006_register.validate_log(self.log, self.register)
        self.assertEqual(
            ["footage_loss", "misleading_labels", "thermal_load", "rendering_instability",
             "licensing", "firmware_modification"],
            [item["id"] for item in self.register["risks"]],
        )
        self.assertEqual("fffd5c9a63cb732e103052acae29ae0c251585cc",
                         self.register["implementationBaseRevision"])
        firmware = [item for item in self.log["decisions"] if item["riskId"] == "firmware_modification"]
        allowed = [item for item in self.log["decisions"] if item["decision"] == "allowed"]
        self.assertTrue(firmware)
        self.assertTrue(all(item["decision"] == "deferred" for item in firmware))
        self.assertTrue(all(item["blockedStreamIdentified"] is False and item["recoveryProcedureVerified"] is False
                            for item in firmware))
        self.assertTrue(any(item["irreversible"] is False and item["authorizedByEnthusiasmOnly"] is False
                            and item["riskId"] != "firmware_modification" and "capability" in item["proposal"].lower()
                            for item in allowed))

    def test_firmware_enthusiasm_mutant_is_deferred(self) -> None:
        decision = next(item for item in self.log["decisions"] if item["riskId"] == "firmware_modification")
        proposal = proposal_from(decision)
        proposal["authorizedByEnthusiasmOnly"] = True
        proposal["proposal"] = "Flash modified camera firmware because the user is enthusiastic."
        result = p006_register.assess_proposal(self.register, proposal)
        self.assertEqual(
            {"decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions"},
            set(result),
        )
        self.assertEqual("deferred", result["decision"])
        self.assertIn("enthusiasm-as-authorization", result["rejectedClaims"])
        self.assertTrue(any("non-destructive" in item.lower() for item in result["preservedResults"]))
        self.assertNotEqual("allowed", result["decision"])

    def test_complete_nondestructive_proposal_can_be_allowed(self) -> None:
        proposal = {
            "riskId": "rendering_instability",
            "proposal": "Compare a retained CPU reference against the current renderer on a host fixture.",
            "irreversible": False,
            "blockedStreamIdentified": False,
            "recoveryProcedureVerified": False,
            "authorizedByEnthusiasmOnly": False,
            "alternatives": ["keep the current renderer unchanged"],
            "evidence": ["host fixture with a retained reference frame"],
            "resourceCost": {"value": 2, "unit": "h", "domain": "engineering_time"},
            "fallback": "Discard the candidate renderer and keep the retained reference path.",
            "stopCondition": "Stop if the candidate replaces a source frame or the reference comparison is skipped.",
        }
        result = p006_register.assess_proposal(self.register, proposal)
        self.assertEqual("allowed", result["decision"])
        logged = proposal_from(next(item for item in self.log["decisions"] if item["decision"] == "allowed"))
        self.assertEqual("allowed", p006_register.assess_proposal(self.register, logged)["decision"])

    def test_missing_resource_cost_unit_or_domain_requires_clarification(self) -> None:
        proposal = {
            "riskId": "misleading_labels",
            "proposal": "Spend effort relabeling an advertised capability report.",
            "irreversible": False,
            "blockedStreamIdentified": False,
            "recoveryProcedureVerified": False,
            "authorizedByEnthusiasmOnly": False,
            "alternatives": ["leave the existing label unchanged"],
            "evidence": ["advertised-only report already on disk"],
            "resourceCost": {"value": 4, "domain": "engineering_time"},
            "fallback": "Do not publish a new label.",
            "stopCondition": "Stop if the label would claim a physical measurement.",
        }
        missing_unit = p006_register.assess_proposal(self.register, proposal)
        self.assertEqual("clarification_required", missing_unit["decision"])
        proposal["resourceCost"] = {"value": 4, "unit": "h"}
        missing_domain = p006_register.assess_proposal(self.register, proposal)
        self.assertEqual("clarification_required", missing_domain["decision"])

    def test_recovered_firmware_proposal_is_still_not_allowed(self) -> None:
        decision = next(item for item in self.log["decisions"] if item["riskId"] == "firmware_modification")
        proposal = proposal_from(decision)
        proposal["blockedStreamIdentified"] = True
        proposal["recoveryProcedureVerified"] = True
        result = p006_register.assess_proposal(self.register, proposal)
        self.assertEqual("deferred", result["decision"])
        self.assertNotIn("enthusiasm-as-authorization", result["rejectedClaims"])

    def test_schema_errors_raise(self) -> None:
        register = deepcopy(self.register)
        register["phase"] = "P005"
        with self.assertRaises(ValueError):
            p006_register.validate_register(register)
        log = deepcopy(self.log)
        log["decisions"][0]["decision"] = "allowed"
        with self.assertRaises(ValueError):
            p006_register.validate_log(log, self.register)
        proposal = proposal_from(self.log["decisions"][1])
        proposal["unexpected"] = True
        with self.assertRaises(ValueError):
            p006_register.assess_proposal(self.register, proposal)


if __name__ == "__main__":
    unittest.main()
