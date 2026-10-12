# ADR 0020: One-click start; the Start click is the intake decision

## Status

Accepted. Approved by Johnathan on October 12, 2026 ("yes that's fine"), after the
change was built and reviewed. It relaxes one sentence of the approved
specification (Profile readiness: "`Intake complete` means every required field has
a known value or explicit `Unknown / To Determine`"); `docs/specification.md` is
amended to match (*[Amendment 2026-10, ADR 0020]*). Behaviour he asked for: remove
the Profile detour before the first requirement.

## Context

After ADR 0019 reshaped the workflow, getting from a new client to the first
requirement still took a detour through the Profile. A new project opened on the
Profile view, the readiness form asked for a next state and a decision note, and
only then did "Start assessment" enable. The consultant had not yet learned
anything about the client, so the form was filled with ceremony rather than facts.
The specification defined `Intake complete` as "every required field has a known
value or explicit `Unknown / To Determine`". For a client who has just been created
that is never true, so the note was a formality typed to get past a gate.

## Decision

1. **The Start click is the intake decision.** `POST /api/projects/{id}/start-assessment`
   runs in one transaction. From the initial state (`Intake started`) it records
   the `Intake complete` readiness transition, with the fixed note "Intake recorded
   when the assessment was started. No required Profile fields were reviewed at this
   point; Profile details are filled in during gap
   analysis.", then creates the assessment. It returns the assessment and the new
   readiness.
2. **History stays.** The transition goes through the same validation and insert as
   the readiness endpoint (`_record_readiness_transition`), so the history is still
   append-only and audited (`profile.readiness_transitioned`, then
   `assessment.created`). Nothing about the stored model changes.
3. **Nothing is bypassed.** A project in `Needs follow-up` is refused with the
   existing reason (409) and nothing is created. A project that already has an
   assessment is refused (409). `POST /assessments` is unchanged and still requires
   an intake state that permits entry.
4. **Profile complete is still required before issue.** The Profile is approved
   once, before anything is issued, by the existing readiness transition and close
   checks. Only the front door is easier.
5. **Both create screens chain the steps.** "Create and start" (first-run Setup) and
   "Create and start assessment" (add a client or project) create the client, the
   project and the assessment, then open the Assessments view, which already lands
   on the first actionable requirement. An existing project with no assessment shows
   one "Start assessment" card instead of the readiness form. The readiness form
   moves into a collapsed "Readiness history (advanced)" section on the Profile.

## Consequences

- **The specification's definition of `Intake complete` is relaxed.** "Every required
  field known or Unknown" no longer gates the start of an assessment; starting the
  assessment is itself the declaration that intake is done, and the Profile is
  completed during gap analysis as ADR 0002 and the progressive profile model
  intend. The stricter condition survives where it matters: `Profile complete`
  ("no unknown remains") is required before gap analysis can finish and before any
  artifact is issued. The specification wording should be aligned the next time
  Johnathan approves a specification change.
- Readiness history for a one-click project has two rows: the initial row and the
  intake-complete row written at Start.
- The same release stops a withdrawn POA&M item from blocking the CMMC readiness
  close (`poam_open`); Closed and Withdrawn are both terminal, as everywhere else.
- The browser's 404 on every page load was `/favicon.ico`, not an API call. The app
  now ships `favicon.svg`. Evidence: `docs/evidence/one-click-start/`.
