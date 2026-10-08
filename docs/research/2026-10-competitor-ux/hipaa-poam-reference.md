# HIPAA POA&M reference format (structure only)

Source: a 2025 HIPAA Plan of Action and Milestones workbook Johnathan has used
with a client, shared on October 8, 2026. **Only its structure is recorded
here.** The workbook and its client content are not committed (see
`docs/local-evidence-operating-boundary.md` and ADR 0016).

## Two sheets, kept apart on purpose

| Sheet | What it holds | Tied to a regulation? |
|---|---|---|
| **HIPAA Controls** | Gaps against cited Security Rule implementation specifications | Yes: each row cites a 45 CFR 164.3xx paragraph |
| **Control Enhancements** | Recommended improvements grouped by control group (for example Security Official, Business Continuity, Disaster Recovery, Incident Response) | No: best practice, not a Security Rule citation |

The split matters for the tool. Today our findings and corrective actions only
attach to framework requirements. Johnathan's deliverable also carries
**recommendations that are not regulatory gaps**, and keeping them on their own
sheet stops a best practice from reading as a legal requirement (ADR 0011).

## Columns

**HIPAA Controls:** POAM ID (`HC-n`) · Requirement Family · Requirement ID
(citation) · Requirement (name) · Requirement Description (rule text) · Finding ·
Risk Rating · Recommendation · Status · Finding Date · Scheduled Completion
Date · Actual Completion Date · Point of Contact · Milestones · Status Summary ·
Resources Needed · Comments · Link to Evidence

**Control Enhancements:** POAM ID (`CE-n`) · Control Group · Control
Description · Risk Rating · Recommendation · Status · Finding Date · Scheduled
Completion Date · Actual Completion Date · Point of Contact · Milestones ·
Status Summary · Resources Needed · Comments · Link to Evidence

## Vocabularies

- **Risk Rating:** H / M / L. The tool's 5×5 inherent/residual risk needs a
  documented mapping to these three bands for client-facing output.
- **Status** (Excel dropdown): Pending, Open, Closed, On-Hold, Cancelled. The
  tool's remediation lifecycle (including "ready for validation" / verified)
  needs a mapping to these, or the deliverable's list should change; to decide
  with Johnathan.

## Layout

Title in row 1, headers in row 2, frozen header row, auto-filter on the header,
grey bold header fill on the enhancements sheet, wide text columns for
description, finding and recommendation.

## What it implies for the tool

1. The HIPAA POA&M export should reproduce this two-sheet workbook.
2. A **recommendation / enhancement** record type is needed alongside findings,
   with a control group instead of a citation.
3. Living fields (Scheduled and Actual Completion, Point of Contact, Milestones,
   Status Summary) are what the monthly service cycle updates; the workbook is
   regenerated each month rather than edited by hand.
4. Requirement name and description come from the pinned catalog, so labels
   stay exact (for example 164.308(a)(7)(ii)(C) is "Emergency mode operation
   plan" in the regulation).
5. Owner and target date should be warned on (not blocked) before issuance; a
   POA&M with blank dates and owners is weak evidence of a plan.

## Still needed

The yearly report narrative itself (Word/PDF), if one exists beyond this
workbook.
