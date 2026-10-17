# P140 — Implement offline search and filtering

Active phase: **P140**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host reference for "Offline search index and deterministic retrieval tests". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Offline search index and deterministic retrieval tests

- Goal: Make the catalogue useful without network dependence or opaque recommendation behavior.
- Method: Index titles, alternate titles, stock names, formats, scene families, and evidence quality. Support typo-tolerant discovery with explicit matching behavior. Keep local user recipes private and allow sorting by relevant technical criteria rather than invented popularity.
- Fixture: A search for a misspelled film title while the phone is offline and a filter for monochrome large-format recipes.
- Oracle: The correct local candidates appear with their evidence status and no network request is required.
- Mutant that must fail: Call a remote language model for every catalogue search.

Machine-readable fixture: [P140_IMPLEMENT_OFFLINE_SEARCH_AND_FILTERING.json](P140_IMPLEMENT_OFFLINE_SEARCH_AND_FILTERING.json).

`scripts/gates/p140_implement_offline_search_and_filtering.py` builds a local token index from each catalogue record's id and text fields. Query tokens are lowercase words. Results are the ids whose index contains every query token, sorted deterministically (lexicographic id, or evidence quality then id). The same query twice returns the same ids. A filter on a field is applied locally to that token hit set and must not drop the query tokens. An empty query performs no remote call and returns an explicit empty id list, not a recommendation or popularity list. `remote_model` true or `network_used` true is rejected. Optional typo tolerance is explicit, off by default, and recorded as a token distance. Private user recipes are withheld from the index. Popularity never ranks or certifies a hit. The evidence id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p140*.py' -v
```

## Non-claims

- This is an authored host reference, not a device probe and not a physical S23 measurement.
- It does not certify sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P140-01 through TC-P140-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
