# P017 — model camera resource ownership

Active phase: **P017**. Entry gates: **P009** and **P016**. This host note does
not re-run those phases and does not claim they were freshly certified here.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. P017
draws a resource-lifetime map for one camera device, one session generation,
surfaces, and images. It does **not** open a physical Galaxy S23. A green host
run is not that measurement.

## Deliverable

Resource-lifetime map and deterministic owner tests.

| Piece | Path |
| --- | --- |
| Lifetime fixture | `docs/P017_MODEL_CAMERA_RESOURCE_OWNERSHIP.json` |
| Owner gate | `scripts/gates/p017_model_camera_resource_ownership.py` |
| Case modules | `scripts/gates/p017_tc01.py` … `p017_tc08.py` |
| Host tests | `scripts/tests/test_p017_*.py` |
| Handoff | `docs/evidence/P017-handoff.json` |
| This note | `docs/P017_MODEL_CAMERA_RESOURCE_OWNERSHIP.md` |

The fixture is `schemaVersion` 1, `phase` `P017`, `mapId`
`s23-resource-lifetime-fixture`, implementation base
`d4deac8fc82832fd23396a01065c5f0bf9da6670`.

## Method, fixture, oracle, mutant

Method: closeable leases with generation identity. Application-owned capture
work (camera device, session, image) is separate from Activity surface
attachment. Failure is a typed event. Open leases close in reverse dependency
order: image, surface, session, camera device.

Fixture: a session callback arriving after its Activity has been recreated and
its previous surface released. Activity generation is 2. The callback is
generation 1 and names `Surface#prev`. That surface is already `released` and
its `objectRef` is still non-null.

Oracle: the callback cannot attach to the new generation or double-close a
resource; the active preview remains valid. `assess_ownership` decides
`stale_ignored`. `surface-active` stays in `preservedResults`. `surface-prev`
is not closed again. Orphaned generation-1 image and session leases are
released, image before session. `camera-1` stays open because the current
session still depends on it.

Mutant: reuse a surface solely because its previous object reference is
non-null. `reuseSurfaceBecauseNonNull` true is decision `rejected` with claim
`reuse-non-null-surface`. The preserved inventory is the same correct set.
A non-null `objectRef` alone does not put `surface-prev` back into the live set.

`failure_events` reports `stale_callback`, `attach_refused`,
`double_close_refused`, `released:<id>`, and `preview_retained:<id>`. It does
not emit a reuse event.

Case modules `evaluate` TC-P017-01 through TC-P017-08. Each encodes that case's
intervention, expected response, and negative control. A negative control is
`rejected`. It is never `qualified` or `allowed`. Preserved results keep the
unaffected evidence (current resources, observations, footage, source timing,
queued frames, committed control, clean master, or the single take id).

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p017*.py' -v
```

The phase test loads the fixture, checks the late callback, checks reverse
close order, and checks that the non-null surface mutant is rejected. Case
tests repeat at least two contexts from each case's repetition plan.

## Non-claims

- This note and `P017_MODEL_CAMERA_RESOURCE_OWNERSHIP.json` are an authored
  host fixture, not a device probe and not a physical S23 measurement or
  qualification.
- A host pass does not certify fixed cadence, sensor-derived Log, ten-bit
  fidelity, film-stock fidelity, cinema-camera equivalence, or on-device
  Camera2 close ordering.
- The phase module does not execute TC-P017-01 through TC-P017-08. Those
  modules are separate host evaluators. Their results are not device evidence.
- No Android or Kotlin sources were changed.
- `docs/evidence/P017-handoff.json` has `commit` null and `nextPhase`
  `blocked` because this phase does not publish. That is not physical
  qualification.
