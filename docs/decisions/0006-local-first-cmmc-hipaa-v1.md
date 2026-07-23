# ADR 0006 - Local-First CMMC and HIPAA V1

## Status

Accepted

## Decision

V1 is a fresh-start, local-first internal platform supporting both CMMC Level 2
and a full HIPAA program: Security Rule, Privacy Rule, Breach Notification Rule,
and Security Risk Analysis.

## Context

RainTech needs to use the platform for real CMMC and HIPAA delivery before
introducing hosted access. The prior CMMC-only milestone sequence no longer
matches that need.

## Consequences

- V1 supports separate CMMC and HIPAA workflows over shared platform services.
- SQLite and managed local file storage remain appropriate.
- V1 runs offline on Windows ARM64 and x64.
- V1 stores sanitized assessment material, not actual CUI, PHI, or ePHI.
- Cross-framework mappings, hosted access, and automation remain deferred.
