# P023 — handle interruption and permission changes

Active phase: **P023**. Entry gate: **P022**. This note does not re-run P022.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for interruption and permission faults. It does
**not** measure a physical Galaxy S23. A green host run is not that
measurement and is not physical S23 qualification.

## Deliverable

Interruption policy and permission fault tests.

| Piece | Path |
| --- | --- |
| Policy fixture | `docs/P023_HANDLE_INTERRUPTION_AND_PERMISSION_CHANGES.json` |
| Phase gate | `scripts/gates/p023_handle_interruption_and_permission_changes.py` |
| Case gates | `scripts/gates/p023_tc01.py` … `scripts/gates/p023_tc08.py` |
| Host tests | `scripts/tests/test_p023*.py` |
| This note | `docs/P023_HANDLE_INTERRUPTION_AND_PERMISSION_CHANGES.md` |

The fixture is `schemaVersion` 1, `phase` `P023`, `policyId`
`s23-interruption-permission-fixture`, implementation base
`d4deac8fc82832fd23396a01065c5f0bf9da6670`. Python 3 standard library only.
No network and no device I/O.

## Policy

Method: define responses to permission denial, camera preemption, screen
departure, app backgrounding, and device policy restrictions. Follow the
existing visible stop-and-finalize policy unless a separately qualified
background design is approved. Never silently remove a requested audio track.

Fixture: microphone permission revoked during startup while video samples are
already arriving.

Oracle: the take stops or fails visibly under policy, retains available media,
and cannot be labelled a successful audio recording.

Mutant, which the gate rejects: continue silently as video-only after
requested microphone acquisition fails. `evaluate` on that mutant returns
`rejected` with claim `silent-video-only`. Accepting it as `stopped`,
`failed_visible`, `qualified`, or `allowed` would be the mutant.

`backgroundDesignApproved` true is not a qualified background recording. This
host fixture does not approve one. The decision is never `qualified` or
`allowed`.

Arrived `takeId`, `video-samples`, and `audio-samples` stay in
`preservedResults` when the decision is rejected. A failure does not wipe the
inventory.

`scripts/gates/p023_handle_interruption_and_permission_changes.py`
(`validate_fixture`, `assess_fixture`, `evaluate`, `mutant_payload`) enforces
that shape. The phase module does not import or execute TC-P023-01 through
TC-P023-08. Those case modules are separate host checks:

| Case | Negative that must not pass |
| --- | --- |
| TC-P023-01 | Stale callback resurrects recording or attaches an obsolete surface |
| TC-P023-02 | Requested settings shown as measured values |
| TC-P023-03 | Permanently starting state or silent capture-contract switch |
| TC-P023-04 | Cosmetic consumer blocks irreplaceable source capture |
| TC-P023-05 | Unbounded queue or hidden frame replacement |
| TC-P023-06 | Invalid partial numeric entry reaches the camera |
| TC-P023-07 | False-color overlay or preview grade recorded into a clean master |
| TC-P023-08 | Double release, duplicate publication, or a second take from cleanup |

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p023*.py' -v
```

The command loads the host fixture, checks that startup microphone revocation
stops visibly and keeps arrived video samples, and checks that silent
video-only continuation is rejected. Case tests cover at least two repeats
each. None of this runs on a phone.

## Non-claims

- This is a host fixture, not a device probe and not a physical S23
  measurement or qualification.
- No fixed cadence is certified. No sensor-derived Log, ten-bit fidelity,
  film-stock fidelity, or cinema-camera equivalence is claimed.
- A claimed background-design approval is not a qualified background
  recording. Background recording stays unsupported here.
- Stopping under this policy is not a successful audio recording when the
  requested microphone was not acquired.
- **TC-P023-01 through TC-P023-08 are separate host modules.** The phase
  module did not run them. No on-device result is claimed for them.
- No Kotlin, Gradle, or workflow sources were changed.
