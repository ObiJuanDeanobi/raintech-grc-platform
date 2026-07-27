# Project Operating Model

## Product Spine

```text
Client -> Project -> Profile -> Assessment -> Continuous Remediation
       -> Evidence -> Reports/Documents
```

The project is the engagement boundary. A client can have multiple projects,
such as `CMMC Level 2 2026` and `HIPAA 2026`, without forcing those efforts to
share scope or conclusions.

## Core Data Objects

- `UserAccount`: stable identity used for attribution and approvals.
- `Client`: organization-level identity and contact information.
- `Project`: framework effort, lifecycle, dates, and ownership.
- `ProjectProfile`: progressive current state, target state, and deltas.
- `ProfileSnapshot`: immutable profile state used by issued outputs.
- `FrameworkVersion`: pinned CMMC or HIPAA catalog release.
- `Assessment`: framework-specific scope, lifecycle, and revision chain.
- `AssessmentResult`: requirement or objective status, notes, and validation.
- `Finding`: a gap discovered through assessment or evidence work.
- `POAMItem`: continuous CMMC remediation record linked to findings.
- `ActionItem`: task, evidence request, corrective action, or validation work.
- `EvidenceArtifact`: logical evidence record.
- `EvidenceVersion`: immutable captured or replaced file version.
- `EvidenceMapping`: contextual link and support rationale.
- `Risk`: threat, vulnerability, safeguards, inherent risk, and residual risk.
- `Quote`: versioned estimate inputs, rules, range, and presentation.
- `Template`: governed document structure and named fields.
- `Policy`: governed content and review lifecycle.
- `GeneratedDocument`: editable output linked to its source versions.
- `Report`: previewable and reproducible project output.
- `ReviewSchedule`: recurrence, due date, lead time, and next occurrence.
- `ReviewEvent`: completed review, including no-change outcomes.
- `AuditEvent`: actor, timestamp, action, and changed-record reference.
- `BackupRecord`: backup type, destination, integrity result, and retention state.

## Progressive Project Profile

The onboarding questionnaire creates the first version of the project profile.
The same profile becomes more complete during scoping, gap analysis, evidence
capture, and remediation.

Profile information is separated into:

- Current environment: what exists and is verified now.
- Target environment: the approved intended implementation.
- Implementation deltas: remediation required to reach the target.
- Unknowns: material facts that still require validation.

Issued assessments and reports use immutable profile snapshots. The live project
profile continues evolving without rewriting historical conclusions.

## Assessment and Continuous Work

An assessment is a time-bound, framework-version-pinned snapshot. Findings,
POA&M items, risks, and recurring reviews are project-level records that may
continue across multiple assessments.

Reassessment copies prior answers and references as `Needs Revalidation`.
Prior issued assessments remain unchanged, and open remediation is referenced
rather than duplicated.

## Shared Engines and Framework Boundaries

CMMC and HIPAA share:

- evidence lifecycle
- 5x5 risk calculations
- action queue
- recurring reviews
- audit history
- reports and document governance

They retain separate framework catalogs, statuses, guidance, completeness rules,
and conclusions. Cross-framework mappings are deferred to V2.

## Question Justification Rule

Every intake or profile question must drive at least one of:

- scope or applicability
- CMMC quote range or implementation path
- assessment guidance
- evidence guidance
- risk analysis
- remediation
- report content
- policy or document generation
- future automation

Questions without a downstream decision or output are removed.

## Evidence Rule

An evidence file is stored once and versioned. Each use is represented by a
mapping with its own support rationale and review state. Reuse does not
automatically satisfy a requirement.

`Met` requires mapped evidence or a documented interview/observation record.
Stale evidence creates review work but does not automatically change the
assessment result.

## Work Queue Rule

Findings, risks, POA&M items, evidence requests, and tasks remain distinct
records. A unified action queue projects them into one prioritized working view.

Items requiring validation move to `Ready for Validation`; they do not close
automatically.

## Versioning Rule

- Issued assessments and reports are immutable.
- Corrections create revisions.
- Changed policies or evidence create new versions.
- No-change reviews create review events without new content versions.
- Same-framework catalog updates create a delta and controlled migration.

## Vertical Slice Rule

Build complete workflows instead of disconnected modules. Each slice must:

- begin from an existing client/project context
- persist typed data
- expose the next useful action
- produce an observable result or output
- include audit attribution
- include applicable tests and recovery behavior

## Bloat and Tech-Debt Gates

Every production ticket passes the ticket, design, review, and milestone gates
defined in `docs/agents/tech-debt-gates.md`. That file is the working checklist
and the single source for the gate questions and the accepted-debt requirements.

The following are V1-late enhancements and do not block initial operational use:

- evidence compression and advanced deduplication
- automatic framework-version migration
- generalized report or template designers
- background schedulers or notification services
- generalized plugin, cloud, or RBAC frameworks

## Issue Acceptance Criteria

Each implementation issue must include:

- user outcome
- specification requirements covered
- data objects touched
- explicit non-goals
- why the work is required now
- simplest acceptable implementation
- abstractions and dependencies introduced
- accepted debt and revisit point
- acceptance criteria
- verification commands
- screenshots for UI changes
- migration or fixture impact

## Verification Defaults

Each production slice must run applicable:

- unit and integration tests
- TypeScript type checking
- Python type/static checks selected during foundation work
- linting
- production frontend build
- local API and browser smoke tests
- ARM64/x64 compatibility review

Framework fixture checks must verify the expected catalog counts and stable IDs.

Continuous integration runs the automated portion of these checks on every push
and pull request. Agent self-reporting is not the verification of record.

## Test Depth

Test depth follows consequence, not code coverage. The following logic produces
compliance conclusions or can lose data, and requires real unit tests:

- CMMC scoring, and the assessment-objective to requirement rollup rule
- 5x5 inherent and residual risk calculation, including band boundaries
- HIPAA Security Risk Analysis scope-completeness enforcement before issue
- evidence staleness, replacement, detachment, and mapping lifecycle
- reassessment carry-forward and `Needs Revalidation` state
- immutability of issued assessments and reports, and revision creation
- backup retention limits and restore verification

Presentation, layout, and navigation do not require unit tests. They are verified
by type checking, production build, and visual review at the supported viewports.
