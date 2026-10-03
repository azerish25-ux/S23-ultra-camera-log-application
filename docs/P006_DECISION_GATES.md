# P006 — decision and risk gates

Active phase: **P006**. Entry gate: **P005**. Deliverable: a risk register and a
phase-entry decision log.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. P005's
measurement registry is the entry condition for this planning gate. This phase
does not change the Android app, camera paths, build pins, or preserved
directive package.

## Purpose

High-risk work is conditional on demonstrated benefit, not fascination with
low-level access. Reversible experiments come first. A gate records
alternatives, evidence, resource cost (`value`, `unit`, and `domain`), a
fallback, and an explicit stop condition.

A firmware proposal with no identified blocked stream and no verified recovery
procedure is deferred. User enthusiasm is not flash authorization.

## Register

[`RISK_REGISTER.json`](RISK_REGISTER.json) is schema version 1, register
`s23-risk-register`, bound to implementation base revision
`fffd5c9a63cb732e103052acae29ae0c251585cc`. It lists six risks:
`footage_loss`, `misleading_labels`, `thermal_load`, `rendering_instability`,
`licensing`, and `firmware_modification`. Each risk records whether the harm is
irreversible, the evidence required before that harm is accepted, a reversible
alternative, and a stop condition.

## Decision log

[`PHASE_ENTRY_LOG.json`](PHASE_ENTRY_LOG.json) records phase-entry decisions
against that register:

- `P006-DEC-firmware-deferred` defers a firmware flash that has no identified
  blocked stream and no verified recovery procedure.
- `P006-DEC-capability-discovery` allows a non-destructive, application-level
  capability inventory that must stay labeled advertised-only.
- `P006-DEC-footage-delete-deferred` defers deletion of original footage until
  a hash-verified copy and restore path exist.

Logged decisions are only `deferred` or `allowed`, and each one must match the
assessor. A logged `allowed` decision is never firmware modification and never
enthusiasm-only.

## Assessor

`scripts/gates/p006_register.py` is standard-library-only. `validate_register`
and `validate_log` raise `ValueError` on schema errors. `assess_proposal`
returns `decision`, `reasons`, `rejectedClaims`, `preservedResults`, and
`openQuestions`.

- Firmware modification, or any irreversible proposal, without both
  `blockedStreamIdentified` and `recoveryProcedureVerified` is `deferred`.
- `authorizedByEnthusiasmOnly` is `deferred` and rejects the claim
  `enthusiasm-as-authorization`. Non-destructive capability and
  application-level investigations remain available.
- A complete non-destructive proposal whose risk is not firmware modification
  can be `allowed`.
- A resource cost missing `unit` or `domain` is `clarification_required` when
  the proposal is not already deferred for safety or enthusiasm. Recording a
  blocked stream and a recovery procedure still does not authorize a flash.

## Test

From the repository root:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p006_register.py' -v
```

The test loads `docs/RISK_REGISTER.json` and `docs/PHASE_ENTRY_LOG.json`,
validates them, checks that the firmware enthusiasm mutant is deferred, and
checks that a complete non-destructive proposal can be allowed.

## Non-claims

- This phase does not qualify a physical S23, a thermal limit, a licence, or a
  sustained camera stream.
- No firmware flash, bootloader change, or protection change is authorized.
- TC-P006-01 through TC-P006-08 are not executed by `scripts/gates/p006_register.py`
  or by this note. Those acceptance cases belong to separate gate modules.
