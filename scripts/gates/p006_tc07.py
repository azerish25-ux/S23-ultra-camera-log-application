"""TC-P006-07 concurrent collaborator change.

Preserve collaborator work across phase handoff. Resetting it for a clean
demonstration is blocked. This host gate does not publish or certify a device.
"""

CASE_ID = 'TC-P006-07'

_KEYS = (
    'caseId',
    'decision',
    'reasons',
    'rejectedClaims',
    'preservedResults',
    'openQuestions',
)


def evaluate(payload):
    """Return the collaborator-handoff decision for one payload.

    Exact keys: caseId, decision, reasons, rejectedClaims, preservedResults,
    openQuestions. reasons, rejectedClaims, preservedResults and openQuestions
    are lists of strings. reasons is non-empty unless decision is "allowed"
    (this case never returns "allowed").
    """
    if not isinstance(payload, dict):
        raise ValueError('payload must be a dict')
    if payload.get('caseId') != CASE_ID:
        raise ValueError('caseId must be TC-P006-07')

    collaborator = payload.get('collaborator')
    if not isinstance(collaborator, dict):
        raise ValueError('collaborator must be a dict')

    present = _require_bool(collaborator, 'present')
    preserved = _require_bool(collaborator, 'preserved')
    overlapping = _require_bool(collaborator, 'overlapping')
    remote_head_changed = _require_bool(collaborator, 'remoteHeadChanged')
    content = _require_str(collaborator, 'content')
    integrated_revision = _require_str(payload, 'integratedRevision')

    if not present:
        return _seal(
            'unchanged',
            ['no concurrent collaborator modification is present'],
            [],
            [integrated_revision],
            [],
        )

    if not preserved:
        # A clean-demonstration reset must fail even if files overlap or the
        # remote head moved. Collaborator content stays in preservedResults.
        return _seal(
            'blocked',
            ['collaborator work must not be overwritten'],
            ['clean-demonstration-reset'],
            [content],
            [],
        )

    reasons = ['collaborator modification preserved in the exact integrated state']
    if overlapping:
        reasons.append('overlapping assumptions were re-evaluated')
    else:
        reasons.append('separate collaborator files were preserved')
    if remote_head_changed:
        reasons.append('remote head changed before push')

    return _seal(
        'integrated',
        reasons,
        [],
        [content, integrated_revision],
        [],
    )


def _require_bool(mapping, key):
    if key not in mapping or not isinstance(mapping[key], bool):
        raise ValueError('%s must be a bool' % key)
    return mapping[key]


def _require_str(mapping, key):
    if key not in mapping or not isinstance(mapping[key], str):
        raise ValueError('%s must be a str' % key)
    return mapping[key]


def _seal(decision, reasons, rejected_claims, preserved_results, open_questions):
    if decision == 'allowed':
        raise ValueError('TC-P006-07 cannot return allowed')
    lists = {
        'reasons': reasons,
        'rejectedClaims': rejected_claims,
        'preservedResults': preserved_results,
        'openQuestions': open_questions,
    }
    for name, value in lists.items():
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            raise ValueError('%s must be a list of strings' % name)
    if decision != 'allowed' and not reasons:
        raise ValueError('reasons must be non-empty unless decision is allowed')
    result = {
        'caseId': CASE_ID,
        'decision': decision,
        'reasons': list(reasons),
        'rejectedClaims': list(rejected_claims),
        'preservedResults': list(preserved_results),
        'openQuestions': list(open_questions),
    }
    if tuple(result.keys()) != _KEYS:
        raise ValueError('result keys drifted')
    return result
