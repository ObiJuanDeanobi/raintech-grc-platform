# ADR 0001 - Local-First CMMC Level 2 First

## Status

Accepted

## Decision

The platform starts as a local-first CMMC Level 2 application for RainTech internal use.

## Context

The immediate need is conference intake, sales scoping, internal compliance delivery, manual gap analysis, and evidence capture. Hosted customer access, RBAC, and automation are valuable, but they add security and operational complexity before the core workflow is proven.

## Consequences

- SQLite and local file storage are acceptable for early versions.
- CMMC Level 2 is the only compliance framework in scope for V1-V5.
- Hosted deployment, tenant isolation, RBAC, and customer login are deferred to later milestones.
