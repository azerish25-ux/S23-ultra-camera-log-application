# Directive adoption and repository continuity

Adopted 1 October 2026. The root [MASTER_DIRECTIVE.md](../../MASTER_DIRECTIVE.md) establishes the complete [S23 Cinema directive](S23_Cinema_Master_Directive_200000_Words.md) as the governing project specification; [AGENTS.md](../../AGENTS.md) applies it to all implementation work.

## Preserved source

All 20 files from the supplied `S23_Cinema_Master_Directive_Complete_Package(1).zip` are retained unchanged in this directory, with their original relative paths. `PACKAGE_SHA256SUMS.json` records each member's byte length and SHA-256 plus the identity of the uploaded archive. The archive's original top-level folder has been mapped to `docs/master-directive/`; the ZIP container itself is not required for reading or verification.

`INTEGRATION.md` and `PACKAGE_SHA256SUMS.json` are repository integration additions, not parts of the original 20-file package. The original README's statement that no repository files were changed during the package's creation is historical: this adoption is a separate operation. Original runtime identities and red/green logs remain historical evidence and are not represented as this commit's execution logs.

The import preserved 200,208 whitespace-delimited words, 160 phases, 1,280 case specifications, 30 source references and the machine-readable dependency graph. Structural verification and reference checks do not establish application feature completion.

## Existing implementation

The existing application, package ID, build pins, capture paths, tests and media safeguards remain in place. Root README and implementation-status notices distinguish the new specification from earlier implementation milestones. Existing technical notes remain useful subordinate implementation evidence; they cannot shrink the new product mandate or turn untested goals into facts.

The previous GPU-to-P010 readback repair is preserved in commit `d6a25f6caba98ba865b87a7c3a580ba081a77d96`. Its Android workflow is a separate baseline, not physical S23 certification. Temporary import machinery is removed from the final source tree; no transport chunks are part of the application.

## Next implementation gate

Reconcile P001-P004 against the current repository and exact-commit evidence. Produce a requirement-to-implementation map before choosing the next dependency-ready feature. Do not restart existing capture engineering merely to reproduce a reference example, and do not label the full research programme implemented as a result of this documentation import.

Follow the complete directive's evidence classes and acceptance protocols for subsequent work. Physical phone configuration, RAW availability, decoded bit precision, high-resolution throughput, dynamic range, color calibration, thermal endurance and rendering quality remain independent qualification questions until measured.
