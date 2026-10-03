# P022 — protect preview independence

Active phase: **P022**. Entry gate: **P021**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes the monitoring-branch fixture and the host gate that checks clean-master
invariance. It does **not** measure a physical Galaxy S23. A green host run is
not that measurement.

## Deliverable

Monitoring branch contract and clean-master invariance test.

Machine-readable fixture: [P022_PROTECT_PREVIEW_INDEPENDENCE.json](P022_PROTECT_PREVIEW_INDEPENDENCE.json)
(`schemaVersion` 1, `phase` `P022`, `contractId` `s23-preview-independence-fixture`,
implementation base `d4deac8fc82832fd23396a01065c5f0bf9da6670`).

The fixture is one synthetic capture sequence. A false-color overlay, a histogram
update, and a virtual-film preview change repeatedly. Aids are also recorded
disabled. Every sample's `sourceHash` and `recordedHash` stay on the clean master
`1111111111111111111111111111111111111111`. The preview framebuffer hash changes
with the monitoring branch and is never the recording source.

`scripts/gates/p022_protect_preview_independence.py` encodes the method, fixture,
oracle, and mutant:

- Branch monitoring after `source-normalization`.
- The preview has its own downsample (`160x90`), display transform
  (`display-preview`), overlay set, and freshness budget (`750` ms).
- `aid_toggle_hashes` splits recorded hashes by aids enabled and disabled.
- `assess_independence` decides `invariant` when those hashes match the clean
  master and overlays stay on the monitoring branch. `preservedResults` keeps
  the clean-master hash and the sequence id.
- The decision is `withheld` when the aid toggle is incomplete.
- The decision is `rejected` when any sample reuses the composited preview
  framebuffer (`recordedFrom` `preview-framebuffer`, or `recordedHash` equal to
  `previewFramebufferHash`) or the clean master drifts. The rejected claim is
  `composited-preview-as-recording-source` and, when the hash moves,
  `clean-master-drift`. The inventory is not wiped.

`assess_independence` does not call TC-P022-01 through TC-P022-08. Those case
modules are separate host checks. Discovery runs them; this note does not treat
that run as a device session.

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p022*.py' -v
```

The phase test loads the fixture, checks that aids-on and aids-off recorded
hashes match, and checks that copying the preview framebuffer into the recording
source is rejected. That assertion fails if the mutant is implemented.

## Non-claims

- This fixture and note are not a device probe and not a physical S23
  measurement or qualification.
- The host result does not certify fixed cadence without measured evidence,
  sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera
  equivalence.
- `invariant` is a software label for this deterministic hash contract. It is
  not `qualified` and not `allowed`.
- Preview aids, false colour, histogram, and virtual-film are monitoring
  overlays in the fixture. They are not burned into a clean master here, and
  they are not optical or film-stock measurements.
- No Android or Kotlin sources were changed.
- `docs/evidence/P022-handoff.json` leaves `commit` null. This phase does not
  invent a git revision.
