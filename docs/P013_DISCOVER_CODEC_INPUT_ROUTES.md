# P013 — discover codec input routes

Active phase: **P013**. Entry gate: **P012**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture and the gate that inventories codec input routes.
It does **not** measure a physical Galaxy S23. A green host run is not that
measurement.

This is a host fixture. HEVC Main10 advertising is not proof of every ten-bit
input route. A P010 developer and an EGL surface encoder have different
prerequisites.

## Deliverable

Codec-route database and interface-specific qualification plan.

Machine-readable fixture: [P013_DISCOVER_CODEC_INPUT_ROUTES.json](P013_DISCOVER_CODEC_INPUT_ROUTES.json)
(`schemaVersion` 1, `phase` `P013`, `databaseId` `s23-codec-route-fixture`,
implementation base `d4deac8fc82832fd23396a01065c5f0bf9da6670`).

The fixture is an authored inventory, not a camera or codec probe. It records
one codec advertising Main10 with surface input and no usable P010 Image
input. Failures are stored on the candidate that failed. The surface candidate
stays in the inventory.

`scripts/gates/p013_discover_codec_input_routes.py` encodes the phase method,
fixture, oracle, and mutant:

- **Method.** Inventory codec names, profiles, levels, sizes, rates, surface
  support, and byte-buffer or Image formats. Store failures per candidate and
  re-query after relevant device software changes.
- **Fixture.** A codec advertising Main10 with surface input but no usable
  P010 Image input.
- **Oracle.** The surface candidate remains available for testing while the
  CPU P010 developer is honestly unavailable.
- **Mutant.** Use the advertised Main10 profile as the sole P010 acceptance
  criterion. `assess(..., sole_main10_as_p010=True)` returns `rejected` with
  claim `main10-as-sole-p010-criterion`. The surface id stays in
  `preservedResults`. The P010 Image candidate is not promoted to available.
  `candidate_status` does not treat profile `Main10` as acceptance when
  `usable` is false.

`validate_database`, `inventory`, `oracle_holds`, and `assess` enforce that
shape. `assess` returns `caseId`, `decision`, `reasons`, `rejectedClaims`,
`preservedResults`, and `openQuestions`, in that order. The decision is
`interface_specific`, `requalify`, or `rejected`. It is never `qualified` or
`allowed`.

A changed build fingerprint, codec identity, or probe protocol is
`requalify`. Those three strings are the cache identity. A marketing phone
name is not a key. Previous rows stay historical.

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p013*.py' -v
```

The phase test loads `docs/P013_DISCOVER_CODEC_INPUT_ROUTES.json`, checks that
the surface candidate remains available, checks that the CPU P010 developer
stays unavailable, and checks that the Main10-only mutant is rejected without
deleting the surface row. Case modules TC-P013-01 through TC-P013-08 have
their own tests under `scripts/tests/`. Those case modules are not executed
by the phase module.

## Non-claims

- This note and `P013_DISCOVER_CODEC_INPUT_ROUTES.json` are an authored host
  fixture, not a device probe and not a physical S23 measurement.
- No result here qualifies physical S23 capture, fixed cadence without
  measured evidence, sensor-derived Log, ten-bit fidelity, film-stock
  fidelity, or cinema-camera equivalence.
- Main10 advertising does not imply P010 Image support, arbitrary surface
  conversion, or a supported recording badge.
- A host pass does not certify endurance, native resolution, or coexistence
  of every individually supported output.
- The handoff `commit` is null and `nextPhase` is `blocked` because this host
  session does not publish a commit. The next dependency-ready phase id is
  **P014**. That is not a claim that P014 ran.
- No Android or Kotlin sources were changed.
