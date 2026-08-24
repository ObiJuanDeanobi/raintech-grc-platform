# ADR 0014: Governed artifact generation, issuance, and correction

## Status

Accepted. Approved by Johnathan on August 24, 2026 under GitHub issue #50.

## Context

Reports, policies, plans, quotations, and assessment packages are compliance
artifacts. Partial output, silent source drift, or in-place edits to issued
material would make their provenance and approval state unreliable.

## Decision

Generation is complete or fails visibly. A generated artifact records the
engagement, framework version, Profile snapshot, template version, relevant
source-record versions, generation timestamp, and named reviewer or approver.

The minimum final SSP is generated in Slice 3 because it is required for the
CMMC workflow. Slice 6 expands governed report and document capabilities rather
than postponing the minimum SSP until then.

An issuance package contains the final artifacts plus an evidence index and
issuance manifest. Where evidence is included or referenced, those package
records identify the evidence version, SHA-256 value, and verification result.

Presentation-only corrections create a new immutable revision linked to the
prior issued version. A substantive correction reopens the affected source
record, regenerates and rechecks the output, and requires new sign-off. Prior
issued versions remain immutable and retrievable.

Template versions are immutable after use. Changing governed content creates a
new version rather than modifying the historical source of an issued artifact.

## Consequences

Issuance and correction become explicit state transitions. Package contents are
reproducible from recorded inputs, and later corrections cannot erase what was
previously issued.

## Traceability

REQ-006, REQ-012, REQ-013, REQ-015 through REQ-017, and REQ-022.
