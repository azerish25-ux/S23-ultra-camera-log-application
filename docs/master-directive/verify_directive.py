"""Validate the delivered Markdown and its machine-readable companion manifest.

Run: python verify_directive.py /path/to/S23_Cinema_Master_Directive_200000_Words.md
This verifies document structure, not the future Android implementation.
"""
from __future__ import annotations
import collections
import hashlib
import json
from pathlib import Path
import re
import sys


def verify(document: Path, manifest_path: Path) -> dict:
    text = document.read_text(encoding='utf-8')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    words = len(text.split())
    assert words >= 200_000, f'Requested length not met: {words}'
    assert words == manifest['word_count_whitespace'], 'Manifest word count mismatch'
    assert f'{words:,} whitespace-delimited words' in text, 'Displayed count mismatch'
    assert text.startswith('# S23 Cinema System\n'), 'Missing document title'
    assert '__WORD_COUNT__' not in text, 'Unresolved assembly marker'
    headings = re.findall(r'^### (P\d{3})\. ', text, re.M)
    case_headings = re.findall(r'^#### (TC-P\d{3}-\d{2})\. ', text, re.M)
    assert len(headings) == len(set(headings)) == 160, 'Invalid phase headings'
    assert len(case_headings) == len(set(case_headings)) == 1280, 'Invalid case headings'
    assert headings == [p['id'] for p in manifest['phases']], 'Phase manifest mismatch'
    assert case_headings == [c['id'] for c in manifest['cases']], 'Case manifest mismatch'
    phase_ids = set(headings)
    graph = {p['id']: p['dependencies'] for p in manifest['phases']}
    assert all(d in phase_ids for ds in graph.values() for d in ds), 'Unknown dependency'
    visiting, complete = set(), set()
    def visit(node: str) -> None:
        assert node not in visiting, f'Dependency cycle at {node}'
        if node in complete:
            return
        visiting.add(node)
        for dependency in graph[node]:
            visit(dependency)
        visiting.remove(node)
        complete.add(node)
    for node in graph:
        visit(node)
    anchors = re.findall(r'<a id="([^"]+)"></a>', text)
    assert len(anchors) == len(set(anchors)), 'Duplicate internal anchor'
    links = set(re.findall(r'\]\(#([^)]+)\)', text))
    assert links.issubset(set(anchors)), f'Unresolved links: {links-set(anchors)}'
    refs = set(re.findall(r'\[\^([^\]]+)\]', text))
    defs = set(re.findall(r'^\[\^([^\]]+)\]:', text, re.M))
    assert refs == defs, f'Footnote mismatch: {refs^defs}'
    assert defs == set(manifest['sources']), 'Source manifest mismatch'
    fenced = False
    blocks = 0
    for line in text.splitlines():
        if line.startswith('```'):
            if not fenced:
                fenced = True
                blocks += 1
            else:
                assert line.strip() == '```', 'Unexpected nested code fence'
                fenced = False
    assert not fenced, 'Unclosed code fence'
    by_phase = collections.Counter(c['phase'] for c in manifest['cases'])
    assert set(by_phase) == phase_ids and set(by_phase.values()) == {8}, 'Incomplete case matrix'
    assert manifest['executed_tests']['catalogue_cases'] == 'specifications_only'
    assert manifest['executed_tests']['physical_s23'] == 'not_run'
    return {
        'status': 'passed',
        'artifact': document.name,
        'word_count_whitespace': words,
        'bytes': document.stat().st_size,
        'sha256': hashlib.sha256(document.read_bytes()).hexdigest(),
        'phases': len(headings),
        'expanded_case_specifications': len(case_headings),
        'source_references': len(defs),
        'code_blocks': blocks,
        'internal_anchors': len(anchors),
        'dependency_graph': 'acyclic',
        'executed_tests': manifest['executed_tests'],
        'scope': 'Document integrity and included host references; not Android or physical-device certification',
    }


if __name__ == '__main__':
    root = Path(__file__).resolve().parent
    document = Path(sys.argv[1]) if len(sys.argv) > 1 else root/'S23_Cinema_Master_Directive_200000_Words.md'
    result = verify(document, root/'directive_manifest.json')
    print(json.dumps(result, indent=2))
