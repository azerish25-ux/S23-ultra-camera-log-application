#!/usr/bin/env python3
"""Verify the original directive package and its governing repository entry points.

This checks documentation integrity, not Android or physical-device capability.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import sys

PACKAGE = Path('docs/master-directive')
MASTER = 'S23_Cinema_Master_Directive_200000_Words.md'
ARCHIVE_SHA256 = '405d94c125b230701932e4561baa1c1b8c0f705218b6cd8dd492a39f9e5ac02f'
MASTER_SHA256 = '6c8b91612767e7f9c733ff4bc908eed2d385cc0250f3239d7cc0b8a4346dfefc'
MEMBERS = frozenset({
    'README.md', MASTER, 'artifact_verification.json', 'directive_manifest.json',
    'verify_directive.py', 'reference/README.md', 'reference/cinema_reference.py',
    'reference/test_reference.py', 'reference/kotlin/Contracts.kt',
    'reference/kotlin/ContractsTest.kt', 'evidence/reference_red.log',
    'evidence/reference_green_initial.log', 'evidence/reference_hardening_red.log',
    'evidence/reference_green.log', 'evidence/kotlin_red.log',
    'evidence/kotlin_green.log', 'evidence/kotlin_red_compile.log',
    'evidence/kotlin_green_compile.log', 'evidence/kotlin_red_stub.kt.txt',
    'evidence/runtime.json',
})


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def regular_file(root: Path, relative: str) -> Path:
    path = PurePosixPath(relative)
    require(not path.is_absolute() and '..' not in path.parts, 'Unsafe package path')
    target = root.joinpath(*path.parts)
    for item in (target, *target.parents):
        require(not item.is_symlink(), f'Symlink is not preserved source: {relative}')
        if item == root:
            break
    require(target.is_file(), f'Missing regular file: {relative}')
    return target


def verify_repository(root: Path) -> dict:
    root = Path(root).absolute()
    package = root / PACKAGE
    require(package.is_dir() and not package.is_symlink(), 'Missing original directive package')
    index = json.loads(regular_file(package, 'PACKAGE_SHA256SUMS.json').read_text(encoding='utf-8'))
    require(index.get('schema_version') == 1, 'Unsupported integrity manifest schema')
    require(index.get('source_archive_sha256') == ARCHIVE_SHA256, 'Source archive identity changed')
    require(index.get('source_archive_bytes') == 311389, 'Source archive length changed')
    require(index.get('source_member_root') == 'S23_Cinema_Master_Directive/', 'Source member root changed')
    entries = index.get('files')
    require(isinstance(entries, dict) and set(entries) == MEMBERS, 'Original package membership changed')
    for name, expected in entries.items():
        data = regular_file(package, name).read_bytes()
        require(len(data) == expected.get('bytes'), f'Source byte length changed: {name}')
        require(hashlib.sha256(data).hexdigest() == expected.get('sha256'), f'Source hash changed: {name}')
    master = package / MASTER
    require(hashlib.sha256(master.read_bytes()).hexdigest() == MASTER_SHA256, 'Master identity changed')
    required_links = {
        'MASTER_DIRECTIVE.md': ['docs/master-directive/' + MASTER, 'AGENTS.md'],
        'AGENTS.md': ['MASTER_DIRECTIVE.md', 'scripts/verify_master_directive.py'],
        'README.md': ['MASTER_DIRECTIVE.md', 'AGENTS.md'],
        'docs/IMPLEMENTATION_STATUS.md': ['../MASTER_DIRECTIVE.md', 'master-directive/INTEGRATION.md'],
        'docs/master-directive/INTEGRATION.md': ['../../MASTER_DIRECTIVE.md', 'PACKAGE_SHA256SUMS.json'],
    }
    for name, links in required_links.items():
        text = regular_file(root, name).read_text(encoding='utf-8')
        for link in links:
            require(link in text, f'Missing governing reference in {name}: {link}')
    for temporary in ['.github/workflows/directive-import-recovery.yml', '.directive-import']:
        require(not (root / temporary).exists(), f'Temporary import machinery remains: {temporary}')
    spec = importlib.util.spec_from_file_location('preserved_directive_verifier', package / 'verify_directive.py')
    require(spec is not None and spec.loader is not None, 'Cannot load preserved structural verifier')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    try:
        structure = module.verify(master, package / 'directive_manifest.json')
    except AssertionError as exc:
        raise ValueError(f'Directive structure failed: {exc}') from exc
    require(structure['word_count_whitespace'] == 200208, 'Original word count changed')
    require(structure['phases'] == 160 and structure['expanded_case_specifications'] == 1280,
            'Original phase/case catalogue changed')
    return {
        'status': 'passed', 'original_files_verified': len(entries),
        'source_archive_sha256': ARCHIVE_SHA256, 'governing_entrypoint': 'MASTER_DIRECTIVE.md',
        'structure': structure,
        'scope': 'Preserved package and repository governance; not Android or physical-device certification',
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        print(json.dumps(verify_repository(args.root), indent=2))
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f'MASTER DIRECTIVE CHECK FAILED: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
