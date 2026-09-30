import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from check_evidence import match_media_identities


class MediaIdentityChecks(unittest.TestCase):
    def setUp(self):
        self.identities = [{"algorithm": "SHA-256", "sha256": f"{i:064x}", "byteCount": 100 + i} for i in range(3)]
        self.reports = [{"verification": {"mediaIdentity": copy.deepcopy(i)}} for i in self.identities]
        self.clips = [{"mediaIdentity": copy.deepcopy(i)} for i in reversed(self.identities)]

    def test_matches_bytes_independently_of_list_order(self):
        match_media_identities(self.reports, self.clips)

    def test_rejects_wrong_movie_with_same_report_count(self):
        self.clips[0]["mediaIdentity"]["sha256"] = "f" * 64
        with self.assertRaises(ValueError):
            match_media_identities(self.reports, self.clips)

    def test_rejects_size_mismatch(self):
        self.clips[0]["mediaIdentity"]["byteCount"] += 1
        with self.assertRaises(ValueError):
            match_media_identities(self.reports, self.clips)

    def test_rejects_duplicate_report(self):
        self.reports[1] = self.reports[0]
        with self.assertRaises(ValueError):
            match_media_identities(self.reports, self.clips)

    def test_rejects_duplicate_clip(self):
        self.clips[1] = self.clips[0]
        with self.assertRaises(ValueError):
            match_media_identities(self.reports, self.clips)

    def test_rejects_missing_identity(self):
        del self.clips[0]["mediaIdentity"]
        with self.assertRaises(ValueError):
            match_media_identities(self.reports, self.clips)

    def test_rejects_malformed_digest_and_lengths(self):
        for change in ({"sha256": "xyz"}, {"sha256": "F" * 64}, {"byteCount": True}, {"byteCount": -1}, {"algorithm": "MD5"}):
            with self.subTest(change=change):
                clips = copy.deepcopy(self.clips)
                clips[0]["mediaIdentity"].update(change)
                with self.assertRaises(ValueError):
                    match_media_identities(self.reports, clips)
