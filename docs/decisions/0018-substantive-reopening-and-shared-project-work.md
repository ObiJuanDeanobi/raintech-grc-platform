# ADR 0018: Substantive reopening carries unchanged work and shares project work

## Status

Accepted. Decided by Johnathan on September 29, 2026 while implementing GitHub
issue #81, in answer to two explicit questions.

## Context

Issue #81 reopens an issued assessment to correct real content. ADR 0014 requires
the prior issue to stay immutable and the correction to be regenerated, rechecked,
and re-signed. The specification says reassessment copies prior state as
`Needs Revalidation`, and that findings, risks, and POA&M items are project-level.
Two choices were left open: how much must be revalidated, and what happens to SRA
risks, which the schema stores per assessment.

## Decision

1. **Revalidation is limited to the affected records.** The reopening names the
   affected records. Only those get a `Needs Revalidation` item, and only they
   block close until revalidated with a note. All other determinations, notes,
   prompt answers, and evidence mappings are copied unchanged, so the successor
   records them as carried over rather than newly verified.
2. **SRA risks are shared project-level records.** The reopened assessment is not
   given copies. Close readiness reads a project's risks for the approved
   Profile, not one assessment's. Findings, corrective actions, risks, and
   evidence files keep their IDs.
3. **A corrective action stays tied to one record across every revision.** The
   one-record-per-action rule moves from the whole project to each assessment,
   and a trigger forbids linking an action to a different record in any revision.
4. **The prior issue stays current until the successor's package is issued.** A
   reopening never supersedes anything on its own. Issuing a package from the
   successor assessment, through the full review, backup, and issue gates, is the
   only event that supersedes the prior issue.

## Consequences

A single-item correction costs one revalidation, not 149. The cost is that
"unchanged" is a human classification: the system records who selected the affected
records and why, but cannot prove an unselected record is unaffected. Reopening
records are append-only and downgrade refuses once any exist.

## Traceability

REQ-008, REQ-009, REQ-015, REQ-016, REQ-019; AC-006; ADR 0007 and ADR 0014.
