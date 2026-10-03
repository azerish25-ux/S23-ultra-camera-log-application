# P030 — publish media transactionally

Active phase: **P030**. Entry gate: **P029**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for a publication state machine and storage-pressure
checks. It does **not** measure a physical Galaxy S23. A green host run is not
that measurement and is not a physical S23 qualification.

## Deliverable

Publication state machine and storage-pressure tests.

Machine-readable fixture:
[P030_PUBLISH_MEDIA_TRANSACTIONALLY.json](P030_PUBLISH_MEDIA_TRANSACTIONALLY.json)
(`schemaVersion` 1, `phase` `P030`, `mapId` `s23-publish-media-fixture`,
implementation base `d4deac8fc82832fd23396a01065c5f0bf9da6670`).

The fixture is a full gallery destination after private recording of
`take-030` succeeds. The provider semantics are `copy`. The public copy is
not durably accepted because destination space is full. Report export then
fails with `report-serialization-exception`. Private staging stays in
recovery. The gallery shows no empty success. The error names `report_export`.

`scripts/gates/p030_publish_media_transactionally.py` encodes the method,
fixture, oracle, and mutant:

- `provider_action` returns `copy` or `move`. It never returns `delete`.
- `mutant_deletes_before_accept` is true on this fixture: the mutant would
  delete private staging before durable accept. `honest_retains_staging` stays
  true. `assess_publication` does not follow the mutant.
- `trace_publication` budgets temporary duplication and does not permit
  redundant-staging cleanup before durable accept and commit.
- `assess_publication` decides `recovery_retained`. Reasons include the
  oracle: the source remains in recovery storage, no empty gallery success is
  shown, and the error identifies the failed publication step.
  `preservedResults` keep the inventory, including `source:take-030`,
  `recovery:take-030`, and `bytes:4096`.
- A document that already deleted staging before durable accept is `rejected`
  with `staging-deleted-before-durable-accept`. The inventory is not wiped.
- After a durable accept, a failed report export decides `media_retained` and
  leaves media discoverable. `publication_recorded` is only a host-fixture
  label for a commit that followed durable accept. It is not `qualified` and
  not `allowed`.

`assess_publication` does not call TC-P030-01 through TC-P030-08. Those case
modules are separate host checks.

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p030*.py' -v
```

The phase test loads the fixture, checks that the full gallery and the report
serialization exception keep the source in recovery, and checks that
implementing the mutant (deleting private staging before durable accept) would
fail. Case modules TC-P030-01 through TC-P030-08 are separate files. This
phase module does not call them. The command above runs their host tests as
well.

## Non-claims

- This note and the JSON fixture are an authored host fixture, not a device
  probe, not a physical S23 measurement, and not a physical S23 qualification.
- The host result does not certify fixed cadence without measured evidence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- `recovery_retained`, `media_retained`, `publication_recorded`, `withheld`,
  and `rejected` are software labels for this fixture. None of them is
  `qualified` or `allowed`.
- Budgeting temporary duplication does not measure a storage provider, a
  gallery grant, or free space on a device.
- No Android, Kotlin, Gradle, or workflow sources were changed.
- `docs/evidence/P030-handoff.json` leaves `commit` null. This phase does not
  invent a git revision.
