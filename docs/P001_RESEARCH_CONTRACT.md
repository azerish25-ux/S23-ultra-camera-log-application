# P001 — research charter and requirement-to-evidence contract

Active work package: **P001**, with **TC-P001-01 through TC-P001-08**. The complete
[Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. None of its
preserved source files, examples or historical evidence was changed.

## What is implemented

`RESEARCH_CHARTER.json` records twenty stable obligations with category, owner,
owning phase, exact minimum phase dependencies, measurement class and required
evidence classes. It preserves the six requested format names and open research
questions separately from accepted findings. These are scope records, not claims
that twenty features or six rendering profiles have shipped.

`REQUIREMENT_EVIDENCE.json` maps every obligation to an explicit disposition and
its evidence references. Initially it accepts **no product claim**. Its one
passing receipt is bounded static inspection at
`c90625ce302b69dd1c193226aeeb492fe04b334b`, including the existing advertised-only
probe and host evidence checker. This is not the full P002 source audit and not
execution of physical camera behaviour.

`verify_research_contract.py` is a read-only, offline, standard-library tool. It
reads independently retained, SHA-256-bound JSON receipts and compares their
individual checks and measurements with the declared aggregate outcome. It
retains passed, failed, blocked, unavailable, not_run and inconclusive outcomes.
Non-passing evidence is a legitimate record, not a validator failure by itself;
using it to justify a supported claim is rejected. A conflicting known receipt
in a selected run cannot be hidden by selecting only its passing neighbours.

A supported finding must cite the right requirement, required independent
classes, matching scope and one exact source revision. A physical claim also
needs physical-capture lineage, declared owned-media inputs and an exact
configuration/duration. A synthetic fixture cannot be promoted by merely
changing its environment label. Unrelated valid narrower findings and research
questions remain in a rejected report.

## Reproduction

Use the existing repository with Git history, Python 3.10 or newer, and Git.
No Android SDK, third-party Python dependency, private cache or network request
is needed by this gate. The wider existing host suite retains its own dependency
requirements.

After this commit has been published:

```sh
python3 scripts/verify_master_directive.py
python3 scripts/verify_research_contract.py --expected-head "$(git rev-parse HEAD)"
python3 -m unittest discover -s scripts/tests -p 'test_research_contract.py' -v
```

On the first development checkout, before committing the new contract, use
`--baseline-ref c90625ce302b69dd1c193226aeeb492fe04b334b`. This bootstrap is allowed
only at the declared adoption revision when that revision has no contract files.
After publication, the baseline must be the actual immediate predecessor, not a
convenient older revision. CI fetches history and supplies its exact checkout SHA.
A missing source revision, incomplete historical contract, missing receipt or
changed input produces a failing exit code rather than an invented pass.

The executable reports JSON to stdout and returns **0** for a consistent contract
or **1** for rejection/missing prerequisites. It never executes commands stored
in receipts, fetches a remote, resets files, writes an index or publishes a commit.
It checks HEAD and read file identities again before returning. Remote-head
reconciliation before an authorized push remains the publisher's responsibility.

## Acceptance coverage

| Case | Executed contract checks |
| --- | --- |
| TC-P001-01 | Reject unsupported physical certainty, excluded/prohibited claims, synthetic/emulator promotion, mismatched configurations; retain narrower software findings. A fabricated well-formed physical record is only a positive schema fixture. |
| TC-P001-02 | Reject the wrong planned SHA and changed inspected source; preserve the old inspection identity across unrelated commits. |
| TC-P001-03 | Reject absent origin, ownership, date or permitted-use context across models, profiles, references and screenshots; reject missing bytes and symlinks. |
| TC-P001-04 | Prefer individual failed/unavailable/not-run results over green summaries; reject stale receipts, cherry-picked runs and invalid known-run measurements. |
| TC-P001-05 | Require finite numeric values, exact units and domains across timing, colour, memory, geometric blur and precision; reject duplicate JSON keys and exponent overflow. |
| TC-P001-06 | Freeze prior policy/evidence records using Git history; reject rewritten thresholds, deleted results and older-baseline bypass; accept a reviewed new policy only while retaining the original failure. |
| TC-P001-07 | Preserve overlapping and unrelated collaborator bytes; detect HEAD changes before and during validation. |
| TC-P001-08 | Run an isolated offline CLI with empty HOME and no private caches; reject a deliberately missing receipt with a concrete reason. |

The suite has twenty-one test methods; repeated subcases are not twenty independent
physical experiments. Set `S23_P001_EVIDENCE_DIR` to an explicit output directory
to retain baseline input, perturbation, receipt bytes, fixture bytes and observed
result for each case. This environment variable affects the test recorder only,
not the read-only validator. CI stores these under its normal evidence artifact.

## Policy and history changes

An existing policy ID, inspection, fixture or evidence entry is immutable.
`current_inspections` explicitly selects the currently reviewed scope. Append a
fresh inspection and move that selector to supersede old evidence; retain the
original records. Historical-only results cannot support current findings.
An optional fixture `git_revision` binds source-text bytes to Git history instead
of to a mutable working file. This keeps old inspections reproducible without
freezing the application's future source code. A new
threshold uses a new versioned ID with `supersedes`, rationale, reviewer and
passing validation-evidence references. Original failing receipts retain their
original policy hash. A retry uses a distinct run identity; it never converts
an old failure into a pass.

A charter change also increments its version and records an amendment naming
affected obligations and validation evidence. Human review declarations are
inspectable records, **not cryptographic authorization**. No schema entry grants
permission to flash firmware, change a bootloader, alter protections or use
third-party media outside its independently established rights.

## Boundaries and next work

This checker validates structured consistency, not arbitrary English sentences,
measurement honesty or genuine phone possession. A hash authenticates bytes,
not the truth of their contents. Real experiments, independent review and the
existing capture/codec checks remain necessary. Receipt schema v1 is a narrow
P001 host contract, not a replacement for Android diagnostic schemas; production
adapters and broader classification belong to P003.

The inspection map is deliberately partial. Source hashes are rechecked within
that declared scope; a changed commit is never labelled a complete new source
audit. More complete requirement-to-production/test mapping is P002. Reproducible
application baseline acceptance is P004; calibrated units, uncertainty and
measurement budgets are P005. The current empty policy list introduces **no new
camera threshold** and weakens none of the existing numerical gates.

See `docs/evidence/P001-tdd-record.json` and the retained TDD archive for local
red/green/mutation identities. Fresh CI results belong to the exact published
commit, not to the preserved master directive's original reference logs.
