# ADR 0002 - Progressive Customer Profile

## Status

Superseded by ADR 0007.

## Decision

The customer profile is built progressively. V1 creates an InitialProfile for intake, readiness, and quoting. V2 gap analysis enriches that into an ImplementationProfile.

## Context

The first intake cannot know the full customer environment. Accurate SSPs, policies, procedures, evidence guidance, and diagrams require details discovered during gap analysis.

## Consequences

- Intake questions stay focused on scope and quote drivers.
- Gap analysis becomes the main profile enrichment workflow.
- Documents are generated from the ImplementationProfile, not intake alone.
