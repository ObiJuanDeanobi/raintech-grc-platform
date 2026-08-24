# ADR 0016: Sanitized template provenance

## Status

Accepted. Approved by Johnathan on August 24, 2026 under GitHub issue #50.

## Context

RainTech templates may originate from client-facing work and may contain
sensitive content or identifying metadata. V1 needs usable governed templates
without placing client source files or intermediate derivatives in Git.
Automated enforcement is deferred.

## Decision

Template templatization may use an external AI-assisted process only after the
source is sanitized outside the repository. Client source files, intermediate
derivatives, CUI, PHI, and ePHI are never committed.

Until automated enforcement is separately approved and implemented, every
template ticket must record:

- the manual sanitization gate;
- the verification step and result;
- the sanitized source or approved output provenance;
- the approving human; and
- Johnathan's approval before release.

Generated templates use named fields and immutable versions. The application
records which template version produced each governed artifact.

## Consequences

The deferred automation does not weaken the release gate. Every template has a
ticket-level audit trail, while sensitive source material remains outside Git.

## Traceability

REQ-005.
