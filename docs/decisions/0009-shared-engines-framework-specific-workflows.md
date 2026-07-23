# ADR 0009 - Shared Engines and Framework-Specific Workflows

## Status

Accepted

## Decision

CMMC and HIPAA share evidence, risk, action, recurring-review, audit, and
reporting engines while retaining separate framework catalogs and guided
assessment workflows.

## Context

The same artifact or action may support several requirements, but CMMC and HIPAA
have different structures, statuses, applicability rules, and conclusions.
Premature normalization would hide meaningful distinctions.

## Consequences

- Evidence may be mapped many-to-many with mapping-specific rationale.
- One 5x5 risk engine supports CMMC and HIPAA through different required fields
  and completeness checks.
- HIPAA is divided into Security, Privacy, Breach Notification, and SRA areas.
- CMMC-HIPAA crosswalking is an explicit future feature, not an implied result of
  shared storage.
