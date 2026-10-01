# S23 Cinema System — complete directive package

The master Markdown contains **200,208 whitespace-delimited words**, including code, references, and expanded laboratory specifications. It defines **160 development phases** across 20 workstreams and **1,280 phase-by-condition test specifications**.

## Contents

- `S23_Cinema_Master_Directive_200000_Words.md`: the complete master directive.
- `reference/`: runnable Python and Kotlin/JVM contract examples and tests.
- `directive_manifest.json`: machine-readable phases, dependencies, adversarial cases, and source references.
- `artifact_verification.json`: document count, hash, and structural verification.
- `verify_directive.py`: standard-library document integrity verifier.
- `evidence/`: actual red and green test logs and runtime identities.

## Read and execute

Read the charter, scientific model, and test methodology first. Use the phase index to select a dependency-ready work package. The entire long document need not be loaded into every coding session; retrieve the active phase and its cross-cutting contracts.

Run the host reference tests using `reference/README.md`. The final results are **53 Python tests passed** and **32 Kotlin/JVM checks passed**. The initial Python cycle covered 48 tests; five additional boundary checks were observed failing before being repaired. Kotlin's complete red run had 32 failing checks before implementation.

The 1,280 catalogue entries are **test specifications, not executed Android tests**. This package does not contain a built Android app or evidence of physical S23 calibration, capture throughput, GPU rendering, thermal endurance, or cinema-camera equivalence.

To recheck the document:

```sh
python verify_directive.py S23_Cinema_Master_Directive_200000_Words.md
```

No repository files were changed or pushed as part of creating this directive.
