# ADR 0008 - Hosted and Public Access Deferred

## Status

Accepted

## Decision

V1 is internal-only. Hosted deployment, authentication, RBAC, client workspaces,
and public intake are deferred until the local workflows have been exercised and
validated.

## Context

Client and public access introduce identity, authorization, tenant isolation,
secure storage, support, and operational requirements. The internal delivery
workflow must be reliable first.

## Consequences

- V1 uses a lightweight Johnathan account selector for attribution, not access
  control.
- No public or QR intake is included in V1.
- V2 introduces hosted storage, authentication, RBAC, and client access.
- Public intake can follow only after hosted controls and internal testing.
