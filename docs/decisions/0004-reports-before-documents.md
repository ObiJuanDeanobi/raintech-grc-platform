# ADR 0004 - Reports Before Documents

## Status

Accepted, with the SSP sequencing portion superseded by ADR 0014 through the
approved GitHub issue #50 reconciliation. The remaining
reports-before-generalized-documents decision stays accepted.

## Decision

Reports should generally be built before the generalized policy and document
library. The minimum authoritative final SSP required for CMMC close is the
explicit exception and belongs in Slice 3 under ADR 0014.

## Context

Reports are operationally useful earlier. They validate that profile, gap, POA&M, and evidence data are being captured correctly. Document generation depends on that data being reliable.

## Consequences

- The historical V4/V5 allocation is replaced by the stable slice allocation in
  `ROADMAP.md`.
- Slice 3 provides only the minimum final SSP needed for CMMC close.
- Slice 6 retains policies, procedures, diagrams, and the broader governed
  document library.
- Document templates should not become a substitute for clean source data.
