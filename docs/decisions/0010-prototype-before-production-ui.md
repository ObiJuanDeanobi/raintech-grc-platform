# ADR 0010 - Prototype Before Production UI

## Status

Accepted

## Decision

Three structurally different throwaway UI variants will be reviewed before the
production application shell is implemented.

## Context

The prior platform direction became difficult to navigate and attempted too
many disconnected features at once. The key unanswered design question is how
the linked project workflow should feel in daily use.

## Consequences

- The prototype is read-only, uses synthetic data, and does not define the
  production architecture.
- Variants differ in hierarchy and workflow, not merely color.
- The selected interaction decisions are recorded before production build work.
- Prototype code is not promoted directly into production.
