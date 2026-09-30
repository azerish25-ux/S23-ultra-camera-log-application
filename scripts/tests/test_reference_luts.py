import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_reference_luts as checker


class ReferenceArchiveTests(unittest.TestCase):
    def assets(self):
        payloads = {name: b'fixture' for name in (*checker.NAMES, 'README.txt', 'reference-vectors.csv')}
        manifest = dict(schemaVersion=1, referenceVersion='S23Log-reference-0.1', customLogRecordingEnabled=False,
            physicalCameraCertified=False, lutSize=8192, interpolation='linear', primaries='BT2020', domain=[0, 1], appCommit='abc',
            files=[dict(name=name, identity=dict(algorithm='SHA-256', sha256=hashlib.sha256(data).hexdigest(), byteCount=len(data))) for name, data in payloads.items()])
        payloads['manifest.json'] = json.dumps(manifest).encode()
        return payloads

    def check(self, payloads, transform=None, commit='abc'):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / 'evidence.tar'
            with tarfile.open(archive, 'w') as tar:
                for name, data in payloads.items():
                    info = tarfile.TarInfo(checker.PREFIX + name); info.size = len(data)
                    if transform: transform(info)
                    tar.addfile(info, io.BytesIO(data))
            with patch.object(checker, 'verify_directory', return_value={'status': 'passed'}) as consumer:
                result = checker.verify_archive(archive, commit)
                consumer.assert_called_once()
                return result

    def test_valid_identities_reach_independent_consumer(self):
        result = self.check(self.assets()); self.assertTrue(result['identitiesMatched']); self.assertEqual('abc', result['appCommit'])

    def test_missing_asset_rejected(self):
        assets = self.assets(); del assets['README.txt']
        with self.assertRaises(ValueError): self.check(assets)

    def test_tampered_bytes_rejected(self):
        assets = self.assets(); assets['README.txt'] = b'tampered'
        with self.assertRaises(ValueError): self.check(assets)

    def test_wrong_source_revision_rejected(self):
        with self.assertRaises(ValueError): self.check(self.assets(), commit='other')

    def test_unsafe_paths_rejected(self):
        with self.assertRaises(ValueError): self.check(self.assets(), lambda info: setattr(info, 'name', '../' + info.name))

    def test_symlinks_rejected(self):
        with self.assertRaises(ValueError): self.check(self.assets(), lambda info: setattr(info, 'type', tarfile.SYMTYPE))

    def test_wrong_curve_contract_rejected(self):
        assets = self.assets(); manifest = json.loads(assets['manifest.json']); manifest['customLogRecordingEnabled'] = True
        assets['manifest.json'] = json.dumps(manifest).encode()
        with self.assertRaises(ValueError): self.check(assets)

    def test_unknown_domain_rejected(self):
        assets = self.assets(); manifest = json.loads(assets['manifest.json']); manifest['domain'] = [-1, 1]
        assets['manifest.json'] = json.dumps(manifest).encode()
        with self.assertRaises(ValueError): self.check(assets)
