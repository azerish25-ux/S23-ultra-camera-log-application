# P012 — discover dynamic-range profiles

Active phase: **P012**. Entry gate: **P011**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture and the profile-combination planner that reads it.
It does **not** measure a physical Galaxy S23. A green host run is not that
measurement and is not physical S23 qualification.

## Deliverable

Profile-combination planner and explicit rejection reasons.

Machine-readable fixture: [P012_DISCOVER_DYNAMIC_RANGE_PROFILES.json](P012_DISCOVER_DYNAMIC_RANGE_PROFILES.json)
(`schemaVersion` 1, `phase` `P012`, `plannerId` `s23-dynamic-range-profile-fixture`,
implementation base `d4deac8fc82832fd23396a01065c5f0bf9da6670`).

The fixture is authored. It is not a camera probe. Sizes, profiles, and latency
numbers are constraints for the host gate.

`scripts/gates/p012_discover_dynamic_range_profiles.py` encodes the phase
method, fixture, oracle, and mutant:

- Method: query ten-bit capability and supported dynamic-range profiles,
  evaluate pairwise or set constraints for preview and recording outputs,
  record additional latency only where a route exposes it, and keep HLG,
  HDR10, SDR, and RAW-derived Log as separate source and encoding categories.
- Fixture: an HLG-capable route (`hlg-record`) that rejects an SDR preview
  (`sdr-preview`) in the same capture request. The pairwise constraint is
  `hlg-rejects-sdr-preview`.
- Oracle: `assess` rejects that mixed combination, or, when `monitoring_route`
  names a usable role-`monitoring` route that is **not** inside the capture
  request (`sdr-monitor`), records `independent_monitor` without putting the
  SDR preview into the HLG request.
- Mutant rejected: HLG support does not imply arbitrary SDR and HDR surface
  coexistence. The claim `hlg-implies-sdr-hdr-coexistence` is recorded and the
  decision is not `candidate`. Removing the fixture constraint does not make
  the mix legal.

`failedProperties` lists `optionalCodecQuery`. One route records `queryError`
`dynamicRangeProfiles`. Neither failure empties the route list. `inventory`
returns every route. `additionalLatencyNs` is copied for `hlg-record`
(8000000) and `hdr10-surface` (12000000) and stays null where it was not
exposed. Null is not replaced with an invented latency.

`assess(document, capture_request, monitoring_route=None)` returns `caseId`
`P012`, then `decision`, `reasons`, `rejectedClaims`, `preservedResults`, and
`openQuestions`. Decisions are `rejected`, `withheld`, `candidate`, or
`independent_monitor`. They are never `qualified` or `allowed`.
`preservedResults` keeps every route identity plus latency tokens only for
exposed values. `candidate` is a host label for one usable profile category,
not physical qualification, ten-bit fidelity, sensor-derived Log, film-stock
fidelity, or cinema-camera equivalence.

## Case modules

`scripts/gates/p012_tc01.py` through `p012_tc08.py` are separate host cases.
Each encodes that case's intervention, expected result, and negative control.
A negative control does not return `qualified` or `allowed`. This note does
not claim those modules were run on a device.

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p012*.py' -v
```

The phase test loads the fixture, checks that HLG, HDR10, SDR, and RAW-derived
Log stay separate, checks that a failed query does not erase other routes,
checks that HLG plus SDR and HDR surfaces in one request is rejected even
without the fixture constraint, and checks that an explicit monitoring route
is not same-request coexistence.

## Non-claims

- This note and `P012_DISCOVER_DYNAMIC_RANGE_PROFILES.json` are a host fixture,
  not a device probe and not a physical S23 qualification.
- No ten-bit fidelity, sensor-derived Log, film-stock fidelity, or
  cinema-camera equivalence is claimed.
- Fixed cadence is not certified. Container timing is out of scope for this
  planner.
- HLG support does not authorize arbitrary SDR and HDR surfaces in one capture
  request. An independent monitoring route is not that coexistence.
- A short host decision does not certify endurance or unlimited recording.
- **TC-P012-01 through TC-P012-08 are host fixtures.** Passing them does not
  produce on-device evidence.
- No Kotlin or Android sources were changed.
