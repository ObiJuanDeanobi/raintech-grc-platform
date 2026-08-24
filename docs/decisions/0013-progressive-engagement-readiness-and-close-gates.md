# ADR 0013: Progressive engagement readiness and close gates

## Status

Accepted. Approved by Johnathan on August 24, 2026 under GitHub issue #50.

## Context

The approved discovery packet defines one progressive project Profile rather
than separate onboarding and implementation records. It also requires readiness
and close behavior to remain framework-specific. Earlier governance language
did not make the phase transitions or close gates sufficiently explicit.

## Decision

Each engagement uses one progressive Profile that accumulates verified current
state, approved target state, implementation deltas, unknowns, scope counts,
dates, contacts, technology stack, external tools, and data-flow facts.

The application distinguishes these observable readiness states:

- Intake is complete when the required initial fields are present.
- Assessment work may begin at intake-complete and proceed through continuous
  remediation without creating a second profile.
- Profile is complete only when no `Unknown / To Determine` value remains.
  Gap-analysis completion and scope-dependent final artifacts require this
  state.
- HIPAA closes only when all applicable records are resolved and the Security
  Risk Analysis is complete.
- CMMC closes only when all 110 requirements are `Met` and no POA&M item remains
  open. Any `Blank`, `Pending`, or `Not Met` requirement blocks close. `Pending`
  never generically creates a POA&M item.

Issued outputs bind to an immutable Profile snapshot. Subsequent profile changes
do not rewrite an issued conclusion.

## Consequences

Readiness becomes testable and cannot be inferred from a single percentage.
Framework-specific close rules remain data-driven. Future work must preserve
one progressive Profile while retaining immutable snapshots for issued output.

## Traceability

REQ-001 and REQ-007 through REQ-011.
