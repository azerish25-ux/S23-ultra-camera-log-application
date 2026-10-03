"""TC-P006-08 independent reproduction.

Reproduce the stated software result or report a concrete missing prerequisite.
Undocumented files and unrecorded manual steps stay unverified. A connected
phone does not turn this host slice into physical S23 qualification.
"""

CASE_ID = 'TC-P006-08'
_PHYSICAL_LIMIT = 'physical S23 qualification remains open'

_KEYS = (
    'caseId',
    'decision',
    'reasons',
    'rejectedClaims',
    'preservedResults',
    'openQuestions',
)


def evaluate(payload):
    """Return the independent-reproduction decision for one payload.

    Exact keys: caseId, decision, reasons, rejectedClaims, preservedResults,
    openQuestions. The list fields are lists of strings. reasons is non-empty
    unless decision is "allowed" (this case never returns "allowed" or "passed").

    Optional payload field tempPath is ignored. Different temporary paths do
    not change a clean reproduction.
    """
    if not isinstance(payload, dict):
        raise ValueError('payload must be a dict')
    if payload.get('caseId') != CASE_ID:
        raise ValueError('caseId must be TC-P006-08')

    reproduction = payload.get('reproduction')
    if not isinstance(reproduction, dict):
        raise ValueError('reproduction must be a dict')

    undocumented = _require_bool(reproduction, 'undocumentedFiles')
    manual = _require_bool(reproduction, 'manualIntervention')
    phone_connected = _require_bool(reproduction, 'phoneConnected')
    if 'missingPrerequisite' not in reproduction:
        raise ValueError('missingPrerequisite must be a str or null')
    missing = reproduction['missingPrerequisite']
    if missing is not None and not isinstance(missing, str):
        raise ValueError('missingPrerequisite must be a str or null')
    stated = _require_str(payload, 'statedSoftwareResult')
    # tempPath is an optional observation about the fresh environment. It is
    # not evidence, a prerequisite, or a physical-qualification input.
    _ = payload.get('tempPath', None)

    if undocumented or manual or missing:
        reasons = []
        if undocumented:
            reasons.append('undocumented files leave the result unverified')
        if manual:
            reasons.append('unrecorded manual intervention leaves the result unverified')
        if missing:
            reasons.append('missing prerequisite leaves the result unverified')
        if phone_connected:
            reasons.append('a connected phone does not establish physical qualification')
        open_questions = [missing] if missing else []
        return _seal('unverified', reasons, [], [stated], open_questions)

    reasons = ['stated software result reproduced from the supplied artifacts']
    if phone_connected:
        reasons.append('a connected phone does not establish physical qualification')
    else:
        reasons.append('no connected physical phone was part of this host reproduction')
    return _seal(
        'reproduced',
        reasons,
        [],
        [stated],
        [_PHYSICAL_LIMIT],
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
    if decision in ('allowed', 'passed'):
        raise ValueError('TC-P006-08 cannot return allowed or passed')
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
