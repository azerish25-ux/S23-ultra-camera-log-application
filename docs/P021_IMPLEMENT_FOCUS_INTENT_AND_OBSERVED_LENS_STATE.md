# P021 — implement focus intent and observed lens state

Active phase: **P021**. Entry gate: **P020**.

This note publishes a **host fixture** for the dual focus model. It does not
measure a physical Galaxy S23. A green host run is not that measurement, and
it is not physical S23 qualification.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This
write-up does not re-run P020 and does not claim that entry gate was freshly
certified here.

## Deliverable

Dual focus model and focus provenance tests.

| Piece | Path |
| --- | --- |
| Focus fixture | `docs/P021_IMPLEMENT_FOCUS_INTENT_AND_OBSERVED_LENS_STATE.json` |
| Dual focus model | `scripts/gates/p021_implement_focus_intent_and_observed_lens_state.py` |
| Focused host tests | `scripts/tests/test_p021_implement_focus_intent_and_observed_lens_state.py` |
| Case modules | `scripts/gates/p021_tc01.py` … `p021_tc08.py` |
| Case tests | `scripts/tests/test_p021_tc01.py` … `test_p021_tc08.py` |
| Handoff | `docs/evidence/P021-handoff.json` |
| This note | `docs/P021_IMPLEMENT_FOCUS_INTENT_AND_OBSERVED_LENS_STATE.md` |

The gate is Python 3 standard library only. It does not use the network and
it does not perform device I/O.

## Method, fixture, oracle, mutant

Method: keep separate control namespaces and units. Confirm physical focus
through available results and expose unknown distance honestly. Virtual focus
may track a subject in relative depth without claiming metric distance.
Recording source sharpness remains independently important.

Fixture: a face selected for virtual focus while the physical lens is focused
on a nearby foreground object.

Oracle: the interface warns that virtual refocusing cannot restore source
detail that was never sharply recorded.

Mutant: overwrite the physical focus-distance field with the virtual focus
target. `assess_model(..., mutant=True)` rejects that claim. The physical
distance field is left as observed. On this fixture that value stays
`unknown`, not the virtual relative depth `0.62`.

## Model

`docs/P021_IMPLEMENT_FOCUS_INTENT_AND_OBSERVED_LENS_STATE.json` has
`schemaVersion` 1, `phase` `P021`, `modelId` `s23-dual-focus-fixture`, and
implementation base `d4deac8fc82832fd23396a01065c5f0bf9da6670`.

| Namespace | Unit | Subject | Distance |
| --- | --- | --- | --- |
| `physical.lens` | `metres` | `nearby_foreground` | `unknown` (no confirming result) |
| `virtual.development` | `relative_depth` | `face` | relative depth `0.62`, not metres |

`claimsMetricDistance` is false. `recordedSharpAtVirtualSubject` is false, so
the projection carries the oracle warning. `independentOfVirtualPlane` is
true: selecting the face does not invent source sharpness.

`scripts/gates/p021_implement_focus_intent_and_observed_lens_state.py`:

- `validate_model` checks the fixture shape, the separate namespaces, and the
  separate units. An unconfirmed physical distance must be null. A confirmed
  distance must be a positive decimal string in metres.
- `project_focus` returns the physical observation and the virtual target
  side by side. It never copies `relativeDepth` into the physical distance.
- `assess_model` returns `caseId`, `decision`, `reasons`, `rejectedClaims`,
  `preservedResults`, and `openQuestions`. Decisions are `warned`,
  `separated`, or `rejected`. They are never `qualified` or `allowed`.
  Unknown physical distance stays an open question. The mutant, a virtual
  metric claim, or sharpness coupled to the virtual plane is `rejected`, and
  the focus inventory remains in `preservedResults`.

A confirmed capture result such as `0.35` metres is displayed as metres on
the physical subject. It does not become the virtual face target.

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p021*.py' -v
```

The phase test loads the JSON fixture, checks that physical metres and
virtual relative depth stay apart, checks the oracle warning, and checks that
the mutant does not overwrite physical focus distance. Each case test covers
that case's negative control and at least two repeats from its repetition plan.

## Cases

The case modules are host evaluations of the P021 repetition plan. They keep
the baseline focus inventory (`physical.distance:unknown`, virtual subject
`face`) even when the negative control fails. None of them returns
`qualified` or `allowed`.

| Case | Negative control |
| --- | --- |
| TC-P021-01 Late callback generation | Delayed callback must not resurrect recording or attach an obsolete surface |
| TC-P021-02 Result differs from request | Requested settings must not be shown as measured values |
| TC-P021-03 Interruption during transition | Permanently starting, or a silent capture-contract switch, fails |
| TC-P021-04 Preview consumer stalls | A cosmetic consumer must not block source capture |
| TC-P021-05 Source queue exhaustion | An unbounded queue or hidden frame replacement fails |
| TC-P021-06 Draft control recreation | An invalid partial numeric entry must not reach the camera |
| TC-P021-07 Independent monitoring toggle | A false-color overlay or preview grade must not enter the clean master |
| TC-P021-08 Double stop and repeated cleanup | Double release, duplicate publication, or a second take fails |

`assess_model` does not execute those modules.

## Non-claims

- This fixture is not a live S23 probe. No physical Galaxy S23 was focused,
  opened, or qualified. No sensor, lens, firmware, or on-device session is
  certified by these files.
- Unknown physical distance is `unknown`. It is not a measured or invented
  metre value, and it is not the virtual face target.
- Virtual relative depth is not metric distance, not dioptres, and not a
  restored sharp recording of the face.
- A host pass does not certify fixed cadence, sensor-derived Log, ten-bit
  fidelity, film-stock fidelity, cinema-camera equivalence, or endurance.
- No Kotlin or Android sources were changed.
- The handoff commit is null and `nextPhase` is `blocked` until publication.
  That is not a claim that P021 is physically complete. The next dependency
  in the directive is P022, and this writer did not publish it.
