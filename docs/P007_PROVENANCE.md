# P007 — provenance ledger, rights state, and attribution

**Entry gate:** P006 (decision and risk gates), as required before this phase.

This note covers the host provenance ledger only. It does not qualify a
physical S23, and it does not re-run P006.

## Deliverable

The phase deliverable is a provenance ledger, a rights-state validator, and an
attribution export:

| Piece | Path |
| --- | --- |
| Ledger | `docs/PROVENANCE_LEDGER.json` |
| Rights-state validator and attribution export | `scripts/gates/p007_ledger.py` |
| Focused host tests | `scripts/tests/test_p007_ledger.py` |

Implementation identity recorded on the ledger:

- `schemaVersion`: 1
- `phase`: `P007`
- `ledgerId`: `s23-provenance-ledger`
- `implementationBaseRevision`: `fffd5c9a63cb732e103052acae29ae0c251585cc`
- `identityPolicy`: `sha256`

Every stock profile, image, and other imported or generated record in the
ledger carries a local id, a sha256 content id, a display name, a rights
state, source attribution (`origin`, `owner`, `acquiredAt`, `permittedUse`),
and a transformation history. The two `AWG3-stock` profiles share a display
name and differ in sha256, so they are different versions. The image record
has `rights` `unknown` and `publicBundle` false. Digests are of authored
fixture labels. The manifest does not embed media bytes.

`scripts/gates/p007_ledger.py` (Python 3 standard library only):

- `validate_ledger(ledger)` rejects any string containing `token` or `Bearer`,
  rejects an email-shaped `@` address, rejects a missing or malformed sha256,
  and rejects a duplicate sha256. Duplicate display names are allowed.
- `public_bundle(ledger)` returns local ids whose `rights` are exactly
  `permitted`. Unknown rights are left out of redistribution.
- `attribute(ledger, localId)` exports `localId`, `sha256`, `displayName`,
  `origin`, `owner`, `acquiredAt`, `permittedUse`, `rights`, and
  `transformations`. A missing local id raises `KeyError`. Attribution still
  works for an unknown-rights record so private comparison stays available.
- `assess_identity(records)` reports `decision`, `reasons`, `rejectedClaims`,
  `preservedResults`, and `openQuestions`. A ledger whose `identityPolicy` is
  `sha256` keeps same-name, different-hash records distinct and lists both
  sha256 values. `keyedByDisplayName: true` does not collapse them while the
  policy remains `sha256`. A display-name-only policy is `rejected`. A bare
  record list is assessed as `sha256`.

## Oracle and deliberate mutation

Acceptance oracle: the two identically named `AWG3-stock` profiles are distinct
versions because their sha256 values differ, and the image with unknown
redistribution permission is excluded from the public bundle.

Deliberate mutation: keying identity only by display name
(`identityPolicy` other than `sha256`, with `keyedByDisplayName` true). That
decision is rejected. The two content hashes stay in `preservedResults`.

## How to run

From the repository root:

```bash
python3 -m unittest discover -s scripts/tests -p 'test_p007_ledger.py' -v
```

The test module loads `docs/PROVENANCE_LEDGER.json` from `Path(__file__).parents[2]`.

## Directive cases not executed here

TC-P007-01 through TC-P007-08 are separate modules in the master directive.
They were not run by this host gate. This note does not claim that those cases
passed.

## Non-claims

- No physical S23 qualification, sensor certification, colour certification,
  lip-sync result, firmware result, or on-device measurement is claimed.
- Unknown rights block redistribution through `public_bundle` only. They do
  not block private comparison by default.
- The public manifest contains no media access tokens, email addresses, or
  user identifiers.
- A passing focused unittest shows only the host ledger rules above. It does
  not close licence review for the unknown-rights image, and it does not
  establish that P006 evidence was regenerated in this change.
