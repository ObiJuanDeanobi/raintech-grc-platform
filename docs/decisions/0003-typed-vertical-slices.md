# ADR 0003 - Typed Data and Vertical Slices

## Status

Accepted

## Decision

The platform should be driven by explicit data objects and vertical slices.

## Context

The previous prototype became difficult to navigate because many features appeared at once. A clearer path is to make the data model explicit and build one complete workflow at a time.

## Consequences

- Data objects such as Customer, InitialProfile, ImplementationProfile, QuoteRecommendation, GapAssessment, EvidenceItem, and GeneratedDocument should be modeled deliberately.
- Screens should support workflows instead of becoming disconnected dashboards.
- Acceptance criteria should use real inputs and expected outputs.
