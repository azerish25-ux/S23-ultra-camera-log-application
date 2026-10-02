# P003 — saved-RAW development evidence, first production slice

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. Active scope is
**P003**, with focused coverage under **TC-P003-01 through TC-P003-08**. This change
integrates saved-RAW development with an evidence classifier. It does not finish
the diagnostics, ordinary-camera or live-session adapters, and does not close P004.

## Production behaviour

`RawDevelopmentStore.develop` now creates a unique attempt before its preflight
checks and observes the existing source scan, profile validation, codec
qualification, encoding, decoded-pixel comparison, source re-hashing and output
publication. Those existing algorithms and thresholds remain in place. The
production qualifier is still `LogP010Codec.qualify`; constructor injection exists
only to exercise known faults in instrumentation tests, not as a fallback codec.

The report is retained at:

```
files/exports/raw-development-evidence/attempt-<uuid>.json
```

The existing RAW-development screen exposes **Development attempt reports** for
sharing retained reports. Existing verified movie/colour sidecars are not replaced.
A successful movie sidecar includes the attempt filename; an unavailable or failed
attempt can have a report without pretending it has a verified movie.

Each report binds the application revision, attempt ID, development-device build,
source and profile hashes, source-declared camera/build identity, dimensions, frame
rate, source timestamp span, codec and explicit consent choices. Absent context is
not invented when an earlier step fails. A source header's camera identity is an
input declaration, not independent proof of camera possession or media ownership.

## Stage outcomes and classification

The shared vocabulary has ten independent stages: advertised, configured, source
validation, profile validation, codec qualification, encoded output, decoded
verification, source preservation, publication and physical qualification.
Saved-source processing leaves camera advertisement/configuration and physical
qualification `not_run`; it does not reconstruct a camera session from a filename.

The six outcomes are `passed`, `failed`, `blocked`, `unavailable`, `not_run` and
`inconclusive`. Cancellation becomes `blocked`; exhausted codec qualification
becomes `unavailable`; unexpected exceptions become `failed`. A stopped attempt
retains prior observed outcomes and leaves unreached operations `not_run`.

`verifiedOutput` requires a closed attempt with valid source, profile, codec,
encoded-output, decoded-verification and source-preservation evidence. Publication
is independent: an output can be verified but remain under its partial filename
if the final rename fails. `publishedOutput` additionally requires the no-overwrite
rename to succeed. Neither property certifies physical S23 capture. An independent
physical protocol is deliberately outside this adapter and certification stays
false even for a fully successful synthetic software fixture.

Each observation is retained as an exact UTF-8 JSON payload string with a SHA-256
reference. The Kotlin producer checks its raw facts before assigning a passing
stage. The separate Python consumer recalculates hashes, checks the individual
outcomes and measurements, and derives its own classification rather than trusting
the producer's aggregate flags. Hashes authenticate byte identity, not measurement
honesty. Existing decode/pixel tests remain necessary.

## Existing numerical gates are preserved

The policy ID is `saved-raw-existing-0.9-v1`. Positive codec ramps retain mean error
at most 0.75 code values, peak at most 2, and at least 600 distinct levels. Their
four frames must actually decode as ten-bit data with the existing Log signal
contract. The deliberately eight-bit-degraded control must also decode and fail
those numerical gates; a false `passed` flag without underlying measurements is
not a valid negative control.

Every-frame comparison retains mean luma/chroma limits of 4 code values and peak
64. Source timestamp-span measurements use nanoseconds in the source sensor-time
domain; code errors use `code_value` in `decoded_P010`. The consumer rejects missing
or altered units, policy values, source/profile bindings, frame counts, geometry,
frame rate, interpretation metadata and output/attempt identity. This policy
records existing checks; it does not establish a calibrated sensor precision or
uncertainty budget, which remains separate work.

## Failure and retention boundaries

Checkpoints are written before and after stages through the existing atomic-write
helper. An interruption can leave `closed=false` and an active operation; that is
not completed evidence or a resumable job. Exclusive attempt-file creation prevents
a retry or ID collision from overwriting an earlier report. Source files, imported
profiles and nonempty partial outputs are not deleted by the observer. Each retry
gets a distinct ID. State clears the previous attempt's movie links so a failed
retry cannot present an earlier successful movie as its result.

Report writing is best-effort: failures are exposed separately and must not delete
useful footage. If final persistence fails, the previous checkpoint may remain
incomplete; the UI reports the write issue. A successful output rename followed by
an auxiliary sidecar/library error retains the movie and records that error.
This is not proof against every filesystem, power-loss or provider failure.

## Reproduction and evidence classes

```sh
python3 scripts/verify_master_directive.py
python3 scripts/verify_research_contract.py --expected-head "$(git rev-parse HEAD)"
python3 scripts/verify_repository_continuity.py --expected-head "$(git rev-parse HEAD)"
python3 -m unittest discover -s scripts/tests -p 'test_development_evidence.py' -v
python3 -m unittest discover -s scripts/tests -v
python3 scripts/check_development_evidence.py <attempt.json-or-app-evidence.tar> --expected-revision <app-source-sha>
```

The pure Kotlin classifier can also be executed without Android:

```sh
kotlinc app/src/main/java/com/s23log/probe/core/DevelopmentEvidence.kt scripts/development_evidence_smoke.kt -include-runtime -d /tmp/p003-evidence.jar
java -jar /tmp/p003-evidence.jar
```

The local model runner contains 27 assertions. The independent Python consumer
has 18 tests. `DevelopmentAttemptTest` adds 15 JVM/JUnit methods. Three added
instrumentation methods exercise the actual Android worker with injected
unavailable/cancellation/IO faults, corrupted input, and the real default backend.
They preserve the observed backend outcome; an unavailable backend is not an
encoded-pixel success. The existing native UI test checks the new export button.
CI now passes the actual exported attempts to the independent Python consumer.
A missing report archive fails instead of silently counting an unrun integration.

TC-P003-01 rejects unsupported certainty; -02 binds revisions and attempt output;
-03 binds observations and provenance declarations; -04 rejects contradictory
summaries, degraded ramps and incomplete decoding; -05 requires measurement domains;
-06 rejects rewritten thresholds; -07 preserves source and earlier attempt records;
-08 reopens reports with an isolated consumer. These are focused cases for this
adapter, not execution of every repetition of the full P003 catalogue.

## Source continuity and remaining work

A new immutable inspection is appended for the changed code. P001/P002 historical
inspections, receipts and CI capsule remain intact. The current map points to the
new source revision. Historical 835f67a JUnit results are no longer presented as
execution of changed code: current map entries say `not_run` until separately
reported exact-commit CI is inspected. That is an evidence-scope distinction, not
removal of a regression test; the Android workflow still executes the whole suite.

Local evidence is recorded in `docs/evidence/P003-host-verification.json`. Actual
Android/JUnit/emulator outcomes are reported separately for the published revision.
Local API type-checking with compile-only stubs is not an Android build or a runtime
pass. No source precision, dynamic range, film-stock fidelity, sustained 4K/8K or
physical S23 capability is certified by this slice.

**Next P003 work:** apply the shared stage discipline to capability diagnostics,
ordinary recording and the live laboratory, with production report adapters and
independent integration tests. Only after the remaining P003 gates are accepted
should P004's formal application baseline be closed. Film rendering, durable jobs,
virtual optics and firmware remain under their original dependency gates.
