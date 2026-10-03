"""Host checks for the P009 camera-route inventory. Not a live S23 probe.

TC-P009-01..08 are separate modules and are not executed here.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "gates"))

from p009_routes import assess_open_mode, plan, validate_inventory


def load() -> dict:
    return json.loads((ROOT / "docs" / "CAMERA_ROUTE_INVENTORY.json").read_text(encoding="utf-8"))


class P009RouteTests(unittest.TestCase):
    def test_inventory_document_validates(self) -> None:
        inventory = load()
        self.assertIsNone(validate_inventory(inventory))
        self.assertEqual(inventory["schemaVersion"], 1)
        self.assertEqual(inventory["phase"], "P009")
        self.assertEqual(inventory["inventoryId"], "s23-route-inventory-fixture")
        self.assertEqual(
            inventory["implementationBaseRevision"],
            "fffd5c9a63cb732e103052acae29ae0c251585cc",
        )
        self.assertEqual(inventory["publicCameraIds"], ["0", "1"])
        self.assertNotIn("2", inventory["publicCameraIds"])
        self.assertGreaterEqual(len(inventory["routes"]), 3)
        for route in inventory["routes"]:
            self.assertEqual(route["openMode"], "logical_owner")
            self.assertIs(route["advertised"], True)

    def test_member_2_plans_with_logical_owner_and_unknown_focal(self) -> None:
        inventory = load()
        planned = plan(inventory)
        member = next(item for item in planned if item["physicalId"] == "2")
        self.assertEqual(member["logicalId"], "0")
        self.assertEqual(member["openId"], "0")
        self.assertEqual(member["openId"], member["logicalId"])
        self.assertNotEqual(member["openId"], "2")
        self.assertEqual(member["focal"], "unknown")
        self.assertIsInstance(member["focal"], str)
        self.assertEqual(member["errors"], {})
        self.assertNotIn("2", inventory["publicCameraIds"])
        encoded = json.dumps(member)
        self.assertNotIn("6.7", encoded)
        self.assertNotIn("lens", encoded.lower())

    def test_front_focal_error_does_not_remove_rear_routes(self) -> None:
        inventory = load()
        planned = plan(inventory)
        self.assertEqual(len(planned), len(inventory["routes"]))
        identities = [(item["logicalId"], item["physicalId"]) for item in planned]
        self.assertIn(("0", None), identities)
        self.assertIn(("0", "2"), identities)
        self.assertIn(("1", None), identities)
        front = next(item for item in planned if item["logicalId"] == "1" and item["physicalId"] is None)
        rear = next(item for item in planned if item["logicalId"] == "0" and item["physicalId"] is None)
        member = next(item for item in planned if item["physicalId"] == "2")
        self.assertEqual(front["errors"], {"focal": "missing"})
        self.assertEqual(front["focal"], "unknown")
        self.assertEqual(front["openId"], "1")
        self.assertEqual(rear["errors"], {})
        self.assertEqual(rear["focal"], 6.7)
        self.assertEqual(rear["openId"], "0")
        self.assertEqual(member["openId"], "0")
        self.assertEqual(member["focal"], "unknown")

    def test_independent_physical_open_is_rejected(self) -> None:
        inventory = load()
        physical_routes = [route for route in inventory["routes"] if route["physicalId"] is not None]
        self.assertGreaterEqual(len(physical_routes), 1)
        for route in physical_routes:
            by_mode = copy.deepcopy(route)
            by_mode["openMode"] = "independent_physical"
            rejected = assess_open_mode(by_mode)
            self.assertEqual(rejected["decision"], "rejected")
            self.assertEqual(rejected["rejectedClaims"], ["independent-physical-open"])
            self.assertNotEqual(rejected["decision"], "logical_owner")
            self.assertIn(route["logicalId"], rejected["preservedResults"])

            by_flag = copy.deepcopy(route)
            by_flag["openPhysicalIndependently"] = True
            flagged = assess_open_mode(by_flag)
            self.assertEqual(flagged["decision"], "rejected")
            self.assertEqual(flagged["rejectedClaims"], ["independent-physical-open"])

            kept = assess_open_mode(route)
            self.assertEqual(kept["decision"], "logical_owner")
            self.assertEqual(kept["preservedResults"], [route["logicalId"]])
            self.assertEqual(kept["rejectedClaims"], [])
            self.assertEqual(kept["openQuestions"], ["focal unknown"])
            self.assertNotIn("6.7", json.dumps(kept))

    def test_logical_owner_preserves_known_focal_route(self) -> None:
        inventory = load()
        rear = next(
            route
            for route in inventory["routes"]
            if route["logicalId"] == "0" and route["physicalId"] is None
        )
        result = assess_open_mode(rear)
        self.assertEqual(
            tuple(result),
            ("decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions"),
        )
        self.assertEqual(result["decision"], "logical_owner")
        self.assertEqual(result["preservedResults"], ["0"])
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["openQuestions"], [])

    def test_validate_rejects_public_listing_of_hidden_member(self) -> None:
        inventory = copy.deepcopy(load())
        inventory["publicCameraIds"] = ["0", "1", "2"]
        with self.assertRaises(ValueError):
            validate_inventory(inventory)


if __name__ == "__main__":
    unittest.main()
