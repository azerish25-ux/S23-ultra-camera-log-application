# P009 — camera-route inventory and routing contract

**Entry gates:** P003 and P004. Both are required before this phase. This host
write-up does not re-run those phases and does not claim they were freshly
certified here.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. P009
enumerates usable camera routes without assuming that a physical camera id is
independently openable. Route identity is the logical owner plus the requested
physical target. Nulls and per-property query errors stay on the route that
produced them.

## Deliverable

Camera-route inventory and routing contract tests:

| Piece | Path |
| --- | --- |
| Inventory fixture | `docs/CAMERA_ROUTE_INVENTORY.json` |
| Routing contract | `scripts/gates/p009_routes.py` |
| Focused host tests | `scripts/tests/test_p009_routes.py` |
| This note | `docs/P009_CAMERA_ROUTES.md` |

`scripts/gates/p009_routes.py` is Python 3 standard library only.

- `validate_inventory(inv)` checks the fixture shape and the oracle routes.
- `plan(inv)` returns one record per route: `logicalId`, `physicalId`,
  `openId`, `focal`, `errors`. `openId` is always `logicalId`, including when
  `physicalId` is set. `focal` is the numeric `focalMm` or `"unknown"`.
  `errors` is that route's `queryErrors` object. An error on one route does
  not drop that route or any other route.
- `assess_open_mode(route)` returns `decision`, `reasons`, `rejectedClaims`,
  `preservedResults`, and `openQuestions`. `openMode` `independent_physical`,
  or a truthy `openPhysicalIndependently` flag, is decision `rejected` with
  rejected claim `independent-physical-open`. Otherwise the decision is
  `logical_owner` and `preservedResults` is `[logicalId]`.

## Inventory

`docs/CAMERA_ROUTE_INVENTORY.json`:

| Field | Value |
| --- | --- |
| `schemaVersion` | 1 |
| `phase` | `P009` |
| `inventoryId` | `s23-route-inventory-fixture` |
| `implementationBaseRevision` | `fffd5c9a63cb732e103052acae29ae0c251585cc` |
| `publicCameraIds` | `["0", "1"]` |

Each route has `logicalId`, nullable `physicalId`, `role`, `focalMm`,
`orientation`, `queryErrors`, `openMode` `logical_owner`, and `advertised`
true.

| logicalId | physicalId | role | focalMm | orientation | queryErrors |
| --- | --- | --- | --- | --- | --- |
| `0` | null | `logical_rear` | 6.7 | 90 | `{}` |
| `0` | `"2"` | `physical_member` | null | null | `{}` |
| `1` | null | `logical_front` | null | null | `{"focal": "missing"}` |

Physical member `"2"` is not in `publicCameraIds`. Its focal metadata is null.
The planner uses logical owner `"0"` for that member and focal `"unknown"`.
It does not invent a lens. The front route's focal error is kept on that
route only. The front orientation is null because this fixture does not
supply one.

## Oracle and deliberate mutation

Acceptance oracle: member `"2"` plans with `openId` `"0"` and focal
`"unknown"`. The rear logical route keeps focal `6.7`. The front focal error
does not remove either rear route.

Deliberate mutation: open every physical member as an independent camera
(`openMode` `independent_physical`, or `openPhysicalIndependently` true).
That decision is rejected. The claim recorded is `independent-physical-open`.

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p009_routes.py' -v
```

The focused test loads `docs/CAMERA_ROUTE_INVENTORY.json`, checks member
`"2"`, checks that the front focal error does not drop the rear routes, and
checks that independent physical open is rejected.

## Non-claims

- This fixture is not a live S23 probe. No physical Galaxy S23 was opened.
  No sensor, lens, firmware, or on-device session is qualified by these files.
- Null focal is `"unknown"`. It is not a measured or invented lens.
- Advertisement in the fixture is inventory data, not operational qualification.
- **TC-P009-01 through TC-P009-08 are separate modules.** This phase did not
  run those modules. Their names in the master directive are partial
  characteristic failure, advertised but unusable route, incompatible output
  combination, firmware cache staleness, ambiguous timing support, geometry
  mismatch, codec interface asymmetry, and physical qualification boundary.
  No result from those modules is claimed here.
- A passing host command above is a fixture and routing-contract check only.
  It does not close P009 physical qualification, and it does not re-certify
  the P003 or P004 entry gates.
