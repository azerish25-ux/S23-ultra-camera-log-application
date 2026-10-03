"""P007 host gate: distinct stock profiles and public-bundle rights."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "gates"))
import p007_ledger


def _load_ledger() -> dict:
    return json.loads((ROOT / "docs" / "PROVENANCE_LEDGER.json").read_text())


class ProvenanceLedgerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ledger = _load_ledger()

    def test_ledger_identity_and_duplicate_display_names(self) -> None:
        self.assertEqual(self.ledger["schemaVersion"], 1)
        self.assertEqual(self.ledger["phase"], "P007")
        self.assertEqual(self.ledger["ledgerId"], "s23-provenance-ledger")
        self.assertEqual(
            self.ledger["implementationBaseRevision"],
            "fffd5c9a63cb732e103052acae29ae0c251585cc",
        )
        self.assertEqual(self.ledger["identityPolicy"], "sha256")
        self.assertIsNone(p007_ledger.validate_ledger(self.ledger))
        stocks = [
            record
            for record in self.ledger["records"]
            if record["kind"] == "stock_profile" and record["displayName"] == "AWG3-stock"
        ]
        self.assertGreaterEqual(len(stocks), 2)
        self.assertEqual(len({record["sha256"] for record in stocks}), len(stocks))
        self.assertEqual(len({record["localId"] for record in stocks}), len(stocks))
        for record in stocks:
            self.assertEqual(record["rights"], "permitted")
            self.assertRegex(record["sha256"], r"^[0-9a-f]{64}$")
            for field in ("origin", "owner", "acquiredAt", "permittedUse"):
                self.assertTrue(record[field])
            self.assertIsInstance(record["transformations"], list)

    def test_permitted_profiles_are_in_the_public_bundle(self) -> None:
        stocks = [
            record
            for record in self.ledger["records"]
            if record["kind"] == "stock_profile" and record["displayName"] == "AWG3-stock"
        ]
        bundle = p007_ledger.public_bundle(self.ledger)
        expected = [
            record["localId"]
            for record in self.ledger["records"]
            if record["rights"] == "permitted"
        ]
        self.assertEqual(bundle, expected)
        for record in stocks:
            self.assertIn(record["localId"], bundle)

    def test_unknown_rights_image_is_excluded_from_the_public_bundle(self) -> None:
        images = [
            record
            for record in self.ledger["records"]
            if record["kind"] == "image" and record["rights"] == "unknown"
        ]
        self.assertGreaterEqual(len(images), 1)
        image = images[0]
        self.assertIs(image["publicBundle"], False)
        self.assertRegex(image["sha256"], r"^[0-9a-f]{64}$")
        bundle = p007_ledger.public_bundle(self.ledger)
        self.assertNotIn(image["localId"], bundle)
        for local_id in bundle:
            record = next(item for item in self.ledger["records"] if item["localId"] == local_id)
            self.assertEqual(record["rights"], "permitted")
        exported = p007_ledger.attribute(self.ledger, image["localId"])
        self.assertEqual(exported["rights"], "unknown")
        self.assertEqual(exported["localId"], image["localId"])

    def test_attribute_export_and_missing_id(self) -> None:
        record = self.ledger["records"][0]
        exported = p007_ledger.attribute(self.ledger, record["localId"])
        self.assertEqual(
            list(exported),
            [
                "localId",
                "sha256",
                "displayName",
                "origin",
                "owner",
                "acquiredAt",
                "permittedUse",
                "rights",
                "transformations",
            ],
        )
        self.assertEqual(exported["sha256"], record["sha256"])
        self.assertEqual(exported["displayName"], record["displayName"])
        self.assertEqual(exported["origin"], record["origin"])
        self.assertEqual(exported["transformations"], record["transformations"])
        with self.assertRaises(KeyError):
            p007_ledger.attribute(self.ledger, "missing-local-id")

    def test_duplicate_sha256_and_missing_sha256_are_rejected(self) -> None:
        duplicated = deepcopy(self.ledger)
        duplicated["records"][1]["sha256"] = duplicated["records"][0]["sha256"]
        with self.assertRaises(ValueError):
            p007_ledger.validate_ledger(duplicated)
        missing = deepcopy(self.ledger)
        del missing["records"][0]["sha256"]
        with self.assertRaises(ValueError):
            p007_ledger.validate_ledger(missing)

    def test_secrets_are_rejected(self) -> None:
        samples = (
            "access-token-abc",
            "Bearer abc.def",
            "person@example.com",
        )
        for secret in samples:
            mutated = deepcopy(self.ledger)
            mutated["records"][0]["owner"] = secret
            with self.assertRaises(ValueError):
                p007_ledger.validate_ledger(mutated)

    def test_sha256_policy_treats_same_display_name_as_distinct(self) -> None:
        stocks = [
            record
            for record in self.ledger["records"]
            if record["displayName"] == "AWG3-stock"
        ]
        for payload in (self.ledger, self.ledger["records"]):
            result = p007_ledger.assess_identity(payload)
            self.assertEqual(result["decision"], "distinct")
            for key in ("decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions"):
                self.assertIn(key, result)
            for record in stocks:
                self.assertIn(record["sha256"], result["preservedResults"])
            self.assertNotIn("displayName-only identity", result["rejectedClaims"])

    def test_display_name_only_policy_is_rejected(self) -> None:
        mutated = deepcopy(self.ledger)
        mutated["identityPolicy"] = "displayName"
        mutated["keyedByDisplayName"] = True
        result = p007_ledger.assess_identity(mutated)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("displayName-only identity", result["rejectedClaims"])
        self.assertTrue(result["reasons"])
        stocks = [
            record["sha256"]
            for record in mutated["records"]
            if record["displayName"] == "AWG3-stock"
        ]
        for digest in stocks:
            self.assertIn(digest, result["preservedResults"])

        still_distinct = deepcopy(self.ledger)
        still_distinct["keyedByDisplayName"] = True
        kept = p007_ledger.assess_identity(still_distinct)
        self.assertEqual(kept["decision"], "distinct")
        for digest in stocks:
            self.assertIn(digest, kept["preservedResults"])


if __name__ == "__main__":
    unittest.main()
