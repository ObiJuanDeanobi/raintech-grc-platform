# ADR 0021: One review-and-issue act; drafts are never stored; the Profile is approved once

## Status

Accepted as built. Implements ADR 0019 decision 4 and the *[Amendment 2026-10]* text
of the specification (Reports and Governance; Profile: "The Profile is approved once
per version"). The change is within the engineering delegation of October 8, 2026
(`AGENTS.md`, "Current delegation"). The specification is not edited here. Ticket #145.

## Context

Issuing a package took about ten sign-off acts (10 for CMMC, 9 for HIPAA): a Profile
review, a Profile approval and a readiness decision with a typed reviewer and typed
evidence, then Generate, Start review, Mark reviewed, Sign off (with a role, a note
and a tick per file), Create backup, Issue, plus the SSP approval for CMMC. Each step
asked the consultant to attest to something the system already knew.

## Decision

1. **Drafts are not stored.** `GET /api/projects/{p}/assessments/{a}/draft` renders the
   package from the data as it is now and streams a ZIP. Nothing is written to
   `source_snapshots`, `generated_packages`, `generated_components` or managed
   storage, so a draft can never be reviewed, backed up or issued. Each call is
   audited as `package.draft_generated`. It skips the readiness and completeness
   checks, uses the approved Profile or else the latest version labelled
   "Profile version N (not yet approved)", and shows "Not yet decided" for anything
   undecided. Every Word section has a `DRAFT — NOT ISSUED` header and the title is
   prefixed; every Excel sheet has a `&CDRAFT` header and the banner in its first
   row; every CSV starts with `DRAFT — NOT ISSUED`; every file name starts `DRAFT_`.
   No new dependency: both Office formats are zipped XML.
2. **Issuing is one act that generates from current data inside the act.**
   `POST /api/projects/{p}/assessments/{a}/issue` (`issuance.review_and_issue`):
   hard-gate check, generate, one sign-off event, automatic backup, issue. The
   reviewer is the account's display name, the note is optional, the role and the
   per-file confirmations are gone. The sign-off event still binds the exact package,
   source snapshot and template hashes and is append-only; its approval text is
   generated ("Reviewed for issue by NAME on DATE.", since it is written before the issue happens). Generation, sign-off and
   backup are committed before issue because `issue_package` takes the write lock.
   A second issue of the same assessment within a minute is refused ("This was just
   issued a moment ago"), so a double click or a retry after a timeout cannot create
   another superseding version.
3. **Hard gates stay hard.** The close check (`api/close.fieldwork_ready`) is
   unchanged and still blocks, answering 409 with its plain-English `groups`. At
   issue time the existing binding checks also still block (template bytes, package
   drift, evidence file integrity). A failed backup returns 409 "Backup failed: …
   Nothing was issued; the last issued version is still current." The failed backup
   is recorded and audited, nothing is issued, and the prior issue stays Current.
   Every failure path writes an audit event with the real reason and the stage it
   happened at: `package.issue_blocked`, `package.issue_failed` (generation, sign-off,
   backup or issue stage), `package.backup_failed`, plus the earlier
   `hipaa_preissuance_backup_failed` and `hipaa_package_issue_failed`. A missing or
   unwritable backup folder is a failed backup (recorded, 409), not a server error; a
   database error at the issue step is audited and returned as a plain 409 "Nothing was
   issued". A failed generation keeps the generator's failed attempt record (it is
   committed, not rolled back) and returns a 500 whose message says nothing was issued.
4. **Warnings never block and need no ticking.** Open corrective work (HIPAA, where
   open work may continue after delivery) and evidence near or past its review date are
   listed under "Worth checking". Recorded Profile unknowns are not a warning: the
   specification says Profile complete means no unknown remains, so they are a hard gate
   (see 5).
5. **The Profile is approved once.** The lifecycle endpoint accepts Draft to Approved;
   the reviewer defaults to the account. Approving also records the readiness
   transition `Profile complete` through the same validation and append-only history
   (recording `Intake complete` first when the project is still at `Intake started`).
   Unresolved required fields still block it. **Profile complete means no unknown
   remains** (specification, Profile readiness; AC-016): when the version still records
   unknowns (an "Unknowns and follow-up" item or an Unknown value) the approval is
   recorded but Profile complete is not, and it never overrides a recorded `Needs
   follow-up`. The call answers "Approved. Profile complete is recorded once the
   follow-up items are resolved." The close check lists each recorded unknown under
   "Profile unknowns to resolve" with a link to the Profile, so Review and issue is
   blocked. Resolution: edit the Profile into a new version without the unknowns and
   approve it; that records Profile complete, from `Needs follow-up` too (no unknowns
   remain, so the transition the state machine already allows is taken). Saving a copied
   version that has inventory items used to fail on a database rule; deleting the
   inventory items before their environment fixes it. Typing `Profile complete` into the
   readiness form is refused ("Approve the Profile version instead."). Draft to
   Reviewed still works at the API so a version left Reviewed can be approved, but
   the app no longer offers it.
6. **Supersession keeps the engine's rule.** A second issue of the same assessment
   from unchanged data is a presentation-only correction and supersedes the first
   (also `POST /packages/{id}/issue-now`). Changed data cannot supersede an issue
   without reopening, as ADR 0018 and the specification require, so the act answers
   "Your data has changed since the last issue. Reopen the assessment to issue a new
   version." A reopened assessment is issued by the same act.

## Migration 0022

Recreates two append-only guards; no row is rewritten and no table changes.
`package_review_events_transition_guard` lets any prior state go to `Ready to issue`
with the role, note and confirmations optional (reviewer name and approval text stay
required; the binding checks are copied unchanged). `profile_lifecycle_must_be_ordered`
lets Draft go straight to Approved. Packages left `In Review` or `Reviewed` keep their
rows and show as Draft, because the lifecycle (Draft, Issued, Superseded) is derived
from issuance rows. Downgrade restores both earlier triggers exactly and discards
nothing. Tested on a 0021 database with an `In Review` package
(`api/tests/test_migration_0022.py`).

## Consequences

- Sign-off acts to issue: 10 to 3 for CMMC (Approve Profile, Approve SSP, Review and
  issue) and 9 to 2 for HIPAA (Approve Profile, Review and issue).
- `POST .../review/transitions` is replaced by `POST .../review/sign-off`, a building
  block the act uses and the tests drive. The UI offers only the act.
- A backup failure leaves one unissued package behind. It reads as Draft and is not
  listed; the next attempt creates another.
- The readiness "completion blockers" now say "Approve the Profile version." in place
  of "Record a named reviewer" and "Record review or approval evidence".
- Evidence: `docs/evidence/issue-145/`.
