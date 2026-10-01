"""Positive and adversarial checks for the preserved master directive import."""
from pathlib import Path
import json
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from verify_master_directive import MASTER, PACKAGE, verify_repository


class MasterDirectiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ['MASTER_DIRECTIVE.md', 'AGENTS.md', 'README.md', 'docs/IMPLEMENTATION_STATUS.md']:
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        shutil.copytree(ROOT / PACKAGE, self.root / PACKAGE)

    def index(self):
        path = self.root / PACKAGE / 'PACKAGE_SHA256SUMS.json'
        return path, json.loads(path.read_text())

    def test_original_package_and_governance_pass(self):
        result = verify_repository(self.root)
        self.assertEqual(result['original_files_verified'], 20)
        self.assertEqual(result['structure']['word_count_whitespace'], 200208)
        self.assertEqual(result['structure']['phases'], 160)
        self.assertEqual(result['structure']['expanded_case_specifications'], 1280)
        self.assertEqual(result['structure']['executed_tests']['physical_s23'], 'not_run')

    def test_truncated_master_is_rejected(self):
        path = self.root / PACKAGE / MASTER
        path.write_bytes(path.read_bytes()[:-1])
        with self.assertRaisesRegex(ValueError, 'byte length'):
            verify_repository(self.root)

    def test_same_length_master_corruption_is_rejected(self):
        path = self.root / PACKAGE / MASTER
        data = bytearray(path.read_bytes())
        data[10] ^= 1
        path.write_bytes(data)
        with self.assertRaisesRegex(ValueError, 'hash changed'):
            verify_repository(self.root)

    def test_companion_code_corruption_is_rejected(self):
        path = self.root / PACKAGE / 'reference/cinema_reference.py'
        path.write_bytes(path.read_bytes() + b'\n')
        with self.assertRaisesRegex(ValueError, 'byte length'):
            verify_repository(self.root)

    def test_missing_original_evidence_is_rejected(self):
        (self.root / PACKAGE / 'evidence/reference_red.log').unlink()
        with self.assertRaisesRegex(ValueError, 'Missing regular file'):
            verify_repository(self.root)

    def test_changed_archive_identity_is_rejected(self):
        path, index = self.index()
        index['source_archive_sha256'] = '0' * 64
        path.write_text(json.dumps(index))
        with self.assertRaisesRegex(ValueError, 'archive identity'):
            verify_repository(self.root)

    def test_removed_member_cannot_hide_missing_source(self):
        path, index = self.index()
        del index['files']['reference/README.md']
        path.write_text(json.dumps(index))
        with self.assertRaisesRegex(ValueError, 'membership'):
            verify_repository(self.root)

    def test_unsafe_manifest_path_is_rejected(self):
        path, index = self.index()
        index['files']['../outside.md'] = {'bytes': 0, 'sha256': '0' * 64}
        path.write_text(json.dumps(index))
        with self.assertRaisesRegex(ValueError, 'membership'):
            verify_repository(self.root)

    def test_symlink_cannot_substitute_original_source(self):
        path = self.root / PACKAGE / 'reference/README.md'
        outside = self.root / 'outside.md'
        outside.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, 'Symlink'):
            verify_repository(self.root)

    def test_missing_master_entry_reference_is_rejected(self):
        (self.root / 'MASTER_DIRECTIVE.md').write_text('# Unrelated document\n')
        with self.assertRaisesRegex(ValueError, 'governing reference'):
            verify_repository(self.root)

    def test_readme_cannot_drop_governing_entrypoint(self):
        (self.root / 'README.md').write_text('# Application\n')
        with self.assertRaisesRegex(ValueError, 'governing reference'):
            verify_repository(self.root)

    def test_temporary_import_workflow_must_be_removed(self):
        path = self.root / '.github/workflows/directive-import-recovery.yml'
        path.parent.mkdir(parents=True)
        path.write_text('name: temporary\n')
        with self.assertRaisesRegex(ValueError, 'Temporary import'):
            verify_repository(self.root)


if __name__ == '__main__':
    unittest.main()
