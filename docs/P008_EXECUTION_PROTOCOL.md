# P008 — agent execution protocol

Active phase: **P008**. The [Master Directive](../MASTER_DIRECTIVE.md) remains
authoritative. This note publishes the operating protocol and handoff schema so
another developer can execute one dependency-ready phase at a time. It does
**not** qualify a physical Galaxy S23, and it does **not** mark every programme
phase complete. A local build, a green host test, or this document is not that
qualification.

P008's directive entry gate is P007. This host write-up does not re-run P007
and does not claim that entry gate was freshly certified here.

## Protocol

Machine-readable copy: [AGENT_PROTOCOL.json](AGENT_PROTOCOL.json)
(`protocolId` `s23-agent-protocol`, `schemaVersion` 1, implementation base
`fffd5c9a63cb732e103052acae29ae0c251585cc`).

Work stays on the existing branch. Do not open a side branch or edit unrelated
phases in parallel.

1. Select the next dependency-ready phase from the master directive and do not open uncontrolled parallel edits.
2. Write a failing test first for that phase before changing implementation code.
3. Implement the smallest correct change that makes the new test pass.
4. Record evidence for the revision, commands, results, failures, and unresolved gates.
5. Integrate on the existing branch `main` with fast-forward publication only.
6. Verify the remote head before an authorized push.
7. When push access is absent, return a truthful blocked report and do not invent a publication.
8. Treat a host gate pass with a pending physical gate as software-verified only.
9. Preserve a concurrent remote commit; do not reset or overwrite collaborator work.
10. Do not treat local build success as completion of every phase.

Publication flags in the protocol object:

| Field | Rule |
| --- | --- |
| `branch` | `main` |
| `fastForwardOnly` | true; no force-push and no history rewrite |
| `verifyRemoteHead` | true; read the remote SHA before an authorized push |
| `blockedWithoutAccess` | true; if credentials or network access are absent, stop and say so |

Completion rule, verbatim: host and physical gates are separate; local build is not phase completion.

`scripts/gates/p008_protocol.py` (`validate_protocol`, `validate_handoff`,
`assess_completion`) enforces that shape. Decisions use this order:

1. `accessAbsent` → `blocked`. Reasons include `no push access`. A non-empty `remoteCommit` is kept.
2. Host gate `passed` while the physical gate is not `passed`, including the mutant that marks every phase complete because the local build succeeded → `software_verified_only`. The same mutant with a host gate that did not pass → `blocked`. `markAllPhasesComplete` adds rejected claim `local-build-completes-programme`.
3. `remoteHeadVerified` false while a remote commit is present, and neither of the above already decided the report → `blocked` (verify the remote head before an authorized push).
4. Host passed, physical passed, remote head verified, `markAllPhasesComplete` false, and access present → `complete`.

`preservedResults` always includes `remoteCommit` when that value is a non-empty string, including when the decision is `blocked` or `software_verified_only`. An empty string is not a commit and is not preserved. A host pass is also recorded under `preservedResults.hostGate` so a narrower software result is not discarded. Physical qualification stays an open question until the physical gate is `passed`.

## Handoff fields

[HANDOFF_SCHEMA.json](HANDOFF_SCHEMA.json) requires exactly these fields:

| Field | Rule |
| --- | --- |
| `phase` | Phase id such as `P008` |
| `caseIds` | Case ids in scope for the handoff (list of strings; may be empty) |
| `changedFiles` | Paths touched for the phase (list of strings; may be empty) |
| `commit` | 40 hexadecimal characters, or JSON `null` only when `nextPhase` is `blocked` |
| `testsRun` | Non-empty list of test commands or names that were actually run |
| `failures` | Failures observed in those runs; empty list only when none were observed |
| `unverified` | List of limits that were not run or not established. Strings only |
| `nextPhase` | Next dependency-ready id such as `P009`, or `blocked` |

A handoff must not add or drop fields. `null` commit on a non-blocked `nextPhase` is invalid. Recording `blocked` is the truthful outcome when push access is missing or the phase cannot be integrated; it is not a synonym for success.

Illustrative shape only (not a publication receipt and not a claim that these cases ran):

```json
{
  "phase": "P008",
  "caseIds": [],
  "changedFiles": [
    "docs/AGENT_PROTOCOL.json",
    "docs/HANDOFF_SCHEMA.json",
    "docs/P008_EXECUTION_PROTOCOL.md",
    "scripts/gates/p008_protocol.py",
    "scripts/tests/test_p008_protocol.py"
  ],
  "commit": null,
  "testsRun": [
    "python3 -m unittest discover -s scripts/tests -p test_p008_protocol.py -v"
  ],
  "failures": [],
  "unverified": [
    "TC-P008-01",
    "TC-P008-02",
    "TC-P008-03",
    "TC-P008-04",
    "TC-P008-05",
    "TC-P008-06",
    "TC-P008-07",
    "TC-P008-08",
    "physical S23 qualification"
  ],
  "nextPhase": "blocked"
}
```

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p008_protocol.py' -v
```

The focused test loads both JSON documents, validates them, and checks the
deliberate mutant (mark every phase complete because the local build succeeded,
physical gate still pending). That mutant must be `software_verified_only` or
`blocked`, never `complete`, and its `remoteCommit` must still be present.

## Cases not run

**TC-P008-01 through TC-P008-08 live in separate modules. This phase did not run those modules.** Their directive names are unsupported certainty, conflicting source revision, missing provenance, contradictory outcomes, measurement without units, uncontrolled threshold revision, concurrent collaborator change, and independent reproduction. No result from those modules is claimed here. Passing the host command above is a protocol-schema check only.
