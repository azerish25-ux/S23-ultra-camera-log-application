# P015 — cache capability evidence safely

Active phase: **P015**. Entry gate: **P014**.

This note is a **host fixture**. It does not measure a physical Galaxy S23.
A green host run is not that measurement, and it is not cinema-camera
equivalence.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative.

## Deliverable

Capability cache invalidation and historical evidence viewer.

Machine-readable fixture: [P015_CACHE_CAPABILITY_EVIDENCE_SAFELY.json](P015_CACHE_CAPABILITY_EVIDENCE_SAFELY.json)
(`schemaVersion` 1, `phase` `P015`, `cacheId` `s23-capability-cache-fixture`,
implementation base `d4deac8fc82832fd23396a01065c5f0bf9da6670`).

The fixture is an authored firmware update. The marketing phone name stays
`Galaxy S23 Ultra`. The build fingerprint and the codec capability response
change. An unaffected front-route report stays in the historical store.

## Method, fixture, oracle, mutant

- **Method.** Key cached probes by build fingerprint, app protocol version,
  route, and codec identity. Separate immutable historical measurements from
  the current selection cache. Revalidate stale candidates on selection and
  retain a reason when a previously working mode becomes unavailable.
- **Fixture.** A firmware update with the same marketing phone name but a
  changed codec capability response.
- **Oracle.** The old report remains inspectable while the current planner
  refuses to certify the changed route from stale data.
- **Mutant.** Key the cache only by the string Galaxy S23 Ultra.

`scripts/gates/p015_cache_capability_evidence_safely.py` enforces that shape:

- `cache_key` uses build fingerprint, app protocol version, route, and codec
  identity. The marketing name is not key material.
- `mutant_key` is the deliberate fault. It returns only `Galaxy S23 Ultra`.
  `assess_selection` does not accept a hit from that key.
- `view_history` returns every immutable historical report with
  `currentCertification` false. A failed or stale selection does not delete
  those reports.
- `current_selection` keeps only selection-cache entries that match the
  current identity and the current capability response. The fixture's stale
  rear candidate is dropped. `mutant_selection` would still keep it; the
  planner must not.
- `assess_selection` returns `caseId`, `decision`, `reasons`,
  `rejectedClaims`, `preservedResults`, and `openQuestions`. On the fixture
  the decision is `withheld`, never `qualified` or `allowed`.
  `preservedResults` includes `hist-firmware-a-hevc-main10` and
  `hist-front-jpeg-unaffected`. Reasons state that the old report remains
  inspectable, that the changed route is not certified from stale data, and
  that the previously working mode is unavailable. The rejected claims include
  `stale-route-certification` and `marketing-name-cache-hit`.
- A selection entry whose identity and capability response match the current
  environment, and whose historical source also matches, is `reused`. Reuse
  is a host cache decision. It is not physical S23 qualification.

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p015*.py' -v
```

The phase test loads `docs/P015_CACHE_CAPABILITY_EVIDENCE_SAFELY.json`, checks
that the old report stays inspectable, checks that the marketing-name mutant
would collide, and checks that the planner still withholds the changed route.
Case modules TC-P015-01 through TC-P015-08 are separate host checks. This
phase module does not execute them.

## Non-claims

- This fixture is not a device probe and not a physical S23 measurement.
  No sensor, lens, firmware flash, or on-device session is qualified here.
- The decision is never `qualified` or `allowed` for physical S23 capture,
  fixed cadence without measured evidence, sensor-derived Log, ten-bit
  fidelity, film-stock fidelity, or cinema-camera equivalence.
- A marketing-name cache hit does not certify a route after the build,
  protocol, codec identity, or capability response changes.
- Historical success is not current operational qualification. Advertisement,
  container size, Main10 advertising, constant container timestamps, and a
  short cold run are not those certifications either.
- **TC-P015-01 through TC-P015-08 are separate modules.** No result from those
  modules is claimed by the phase assessor.
- The handoff commit is null and `nextPhase` is `blocked` until a serializer
  records a commit. The directive successor is P016; this host note does not
  publish that phase.
- No Kotlin or Android sources were changed.
