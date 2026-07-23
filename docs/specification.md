# RainTech GRC Platform Specification

## Status

Approved on July 23, 2026. Production work remains governed by the prototype and
vertical-slice ticket gates.

## Problem

RainTech needs one coherent internal workspace for delivering CMMC Level 2 and
HIPAA compliance projects. Today, client intake, environment understanding, gap
analysis, evidence, risks, remediation, policies, and reports live in separate
tools and files. That makes it difficult to preserve context, reuse evidence,
track continuous remediation, and produce consistent deliverables.

## Target User

V1 has one internal user: Johnathan. A lightweight account selector identifies
the active user and attributes all changes, approvals, and audit events to that
account. V1 does not provide authentication, RBAC, or client access.

## Product Model

```text
Client
  -> Project (for example, CMMC Level 2 2026 or HIPAA 2026)
     -> Progressive Project Profile
     -> Quote
     -> Assessment and Gap Analysis
     -> Findings, Risks, and Continuous Remediation
     -> Evidence
     -> Policies and Documents
     -> Reports
```

The project is the compliance engagement boundary. A client may have multiple
projects, and each project owns its own profile, assessment history, evidence
context, risks, and outputs.

## Primary Workflow

1. Create a client and a framework-specific project.
2. Complete a concise onboarding questionnaire that creates the initial project
   profile and, for CMMC, a preliminary quote.
3. Refine the same profile as scope, evidence, interviews, and gap-analysis work
   reveal the current environment and target implementation.
4. Complete the framework assessment with official text, implementation
   guidance, expected evidence, client-specific checks, notes, and status.
5. Create and manage findings, risks, POA&M or corrective-action work, evidence,
   recurring reviews, and validation.
6. Generate governed policies, documents, and reports from versioned project
   data.
7. Reassess by copying the prior assessment into a new draft, revalidating every
   carried-forward item, and preserving the prior issued assessment unchanged.

## V1 Scope

### Project and Profile

- Create, edit, archive, and restore clients and projects.
- Support project states: Active, On Hold, Completed, and Archived.
- Track engagement phases: Onboarding, Scope, Gap Analysis, Remediation,
  Validation, and Reporting.
- Allow phases to overlap; remediation may begin while gap analysis continues.
- Capture current environment, target environment, and implementation deltas.
- Capture CUI or ePHI flow metadata without storing actual CUI, PHI, or ePHI.
- Update the project profile throughout gap analysis and evidence capture.
- Snapshot the project profile when an assessment or report is issued.
- Preserve profile history and identify who changed what and when.

### Frameworks and Assessments

- Support versioned CMMC Level 2 and HIPAA framework catalogs.
- Pin each assessment to a specific framework version.
- CMMC statuses: Blank, Met, Not Met, and Pending.
- HIPAA supports the same statuses plus N/A with required rationale.
- HIPAA addressable specifications record whether the standard measure,
  an equivalent alternative, or a documented non-implementation decision is
  used.
- A final Met determination requires mapped evidence or a documented
  interview/observation record.
- Requirement views show official text, what to examine, expected evidence,
  notes, status, and rule-based client-specific implementation guidance.
- CMMC uses a requirement-centered workspace with its assessment objectives
  visible together.
- HIPAA projects contain four connected areas: Security Rule, Privacy Rule,
  Breach Notification Rule, and Security Risk Analysis.
- Assessments move from Draft to Issued. Issued assessments are immutable;
  corrections create a documented revision.

### Reassessment and Framework Changes

- Create reassessments as copies of prior assessments.
- Carry forward answers, findings, risks, and evidence links as Needs
  Revalidation rather than treating them as newly verified.
- Preserve the prior assessment unchanged.
- Reuse evidence references without duplicating files.
- Show confirmed, changed, newly added, and unresolved items.
- Carry open project-level findings and POA&M items forward without duplication.
- Generate same-framework version deltas for added, changed, retired, or
  renumbered requirements.
- Require explicit review before carrying an answer or evidence mapping into a
  newer framework version.

### CMMC Quote and Scoring

- Generate a preliminary, non-binding CMMC implementation estimate from the
  project profile using editable and versioned pricing rules.
- Support Preliminary, Internally Validated, and Superseded estimate states.
- Allow validation whenever sufficient environment facts are confirmed; it does
  not require the gap analysis to be complete.
- Snapshot the profile inputs and pricing-rule version used by each estimate.
- Ask directly whether the intended path is an enclave or full tenant; do not
  create a separate "scope unclear" package.
- Support enclave, tenant migration, GCC, GCC High, VDI, readiness, audit sprint,
  CMMC Level 1, and recurring-service paths.
- Begin with these editable pricing baselines:
  - GCC enclave plus CMMC Level 2 preparation: $40,000-$75,000.
  - Full GCC tenant migration plus preparation: $60,000-$120,000.
  - GCC High enclave plus preparation: $70,000-$150,000.
  - Full GCC High migration plus preparation: $120,000-$250,000+.
  - VDI-based controlled environment plus preparation: $95,000-$250,000+.
  - Existing GCC hardening plus preparation: $30,000-$65,000.
  - Readiness engagement: $15,000-$45,000.
  - Audit preparation sprint: $20,000-$50,000.
  - CMMC Level 1 engagement: up to $15,000.
  - vCISO plus ongoing compliance: $6,000 per month.
- Provide internal and customer-facing quote views.
- Export a customer-facing PDF titled "CMMC Readiness & Implementation
  Estimate."
- Use only the official CMMC assessment scoring model where scoring applies.
- Do not create a generic readiness score.
- HIPAA quoting remains manual in V1.

### Findings, POA&M, and Continuous Work

- Keep findings, risks, tasks, evidence requests, and POA&M items as distinct
  records surfaced through one unified action queue.
- Use work statuses: Draft, Open, In Progress, Waiting, Ready for Validation,
  Closed, and exceptional Withdrawn.
- CMMC Not Met and Pending results can create linked POA&M work.
- Pending work remains visible until its action is validated.
- A finding reaching Ready for Validation does not close automatically.
- POA&M records belong to the project and continue across assessments.
- Closed items remain historical; failed revalidation may reopen an item or
  create a linked successor.
- Customer-facing POA&M output omits Withdrawn items or leaves their display
  status blank.

### Risk Management

- Use one shared 5x5 likelihood-and-impact engine.
- Retain explicit inherent and residual likelihood, impact, and score.
- Use framework-specific guided views:
  - CMMC focuses on CUI-related threats, vulnerabilities, and safeguards.
  - HIPAA requires complete ePHI scope, flows, threat-vulnerability pairs,
    confidentiality/integrity/availability impact, safeguards, corrective
    actions, acceptance, and review.
- Risk bands are Low 1-4, Moderate 5-9, High 10-16, and Critical 17-25.
- Accepted risks remain active with rationale, owner, and review date.
- High and Critical acceptance requires a named approver.
- Expired acceptance returns to the action queue.
- A HIPAA Security Risk Analysis cannot be issued until every in-scope ePHI
  system, location, and vendor is reviewed or explicitly excluded with rationale.

### Evidence

- Upload through file picker or drag and drop.
- Maintain evidence title, source, capture date, notes, provenance, review date,
  and version history.
- Map one evidence artifact to many requirements, assessment areas, risks, or
  findings.
- Store a mapping-specific explanation of what the artifact supports.
- Reuse evidence without duplicating the underlying file.
- Replace evidence while preserving valid mappings and history.
- Detach a mapping without deleting unrelated mappings.
- Soft-delete evidence through a recycle bin before permanent deletion.
- Archive, compress, and deduplicate superseded evidence where practical.
- Mark stale or overdue evidence without automatically changing Met to Not Met.
- Export evidence with a manifest.

### Policies and Documents

- Maintain reusable, versioned templates and approved content blocks.
- Generate deterministic drafts using named project-profile fields and
  conditional sections; no LLM is required in V1.
- Support editable drafts, version history, linked source data, and approval.
- Policy lifecycle: Internal Draft, Client Review, Approved, Superseded, Retired.
- Create a new version only when content changes.
- A no-change review records a review event and schedules the next review
  without creating a new version.
- V1 document generation includes SSPs, policies, procedures, and other
  template-based deliverables.
- Diagram generation is deferred to V2, but V1 captures structured flow data
  needed for it.

### Recurring Reviews and Notifications

- Apply recurring review rules to evidence, policies, risks, and other eligible
  records.
- Support One-time, Monthly, Quarterly, Semiannual, Annual, and Custom schedules.
- Default reminder lead time is 30 days and is configurable per item.
- Show due-soon and overdue work on the global action queue and project Overview
  when the app opens.
- Completing a no-change review records the event and advances the schedule.

### Reports and Governance

- Preview reports in the browser before export.
- Produce project profile, executive, CMMC gap/score, POA&M, HIPAA gap, HIPAA
  Security Risk Analysis, risk/heatmap, remediation, evidence
  capture/coverage, evidence manifest, policy/review register, and quote reports.
- Support applicable PDF, XLSX, DOCX, and ZIP exports.
- Report lifecycle: Draft, Issued, and Superseded.
- Issued reports capture profile, assessment, framework, and source-data
  versions so they can be reproduced.
- V1 approval records the selected account, date, and optional note.
- Record audit events for profiles, assessments, evidence mappings, policies,
  risks, POA&M items, approvals, and generated outputs.

### Local Operation and Recovery

- Run locally on Windows ARM64 and x64 without requiring a login or internet.
- Use SQLite for structured data and separate managed folders for evidence,
  documents, reports, and backups.
- Provide a double-click launcher and a local browser UI.
- Support a configurable backup destination, including the RainTech OneDrive
  folder for V1.
- Retain 14 daily database/configuration backups and 2 weekly full backups.
- Provide Back Up Now, verified restore, and workspace export/import.
- V1 is designed for sanitized assessment material and does not store actual
  CUI, PHI, or ePHI.

## Navigation

After client and project selection, the workspace uses:

```text
Overview | Profile | Assessments | Actions/POA&M | Evidence |
Risks | Policies | Reports
```

Assessment work contains:

```text
Scope | Gap Analysis | Findings | Validation | History
```

The Overview prioritizes phase, urgent actions, upcoming reviews, project
progress, and recent activity.

## Non-Goals

- Authentication, enforceable RBAC, tenant isolation, or client accounts.
- Public or QR-code intake before hosted deployment and internal validation.
- Storing actual CUI, PHI, or ePHI.
- Automated evidence collection or third-party system integrations.
- Crosswalking CMMC and HIPAA requirements.
- Diagram generation.
- LLM-generated compliance conclusions or freeform policy generation.
- HIPAA certification claims or automated HIPAA pricing.

## Important Edge Cases

- Profile data changes after an assessment or report is issued.
- Evidence supports several requirements but becomes stale for only one use.
- Evidence is replaced or deleted while other mappings remain valid.
- A framework changes while open remediation work continues.
- A copied reassessment contains unresolved prior findings.
- A recurring review is completed with no content change.
- A Pending item is remediated but has not been validated.
- A backup destination is unavailable or a restore package is incomplete.
- Two records are edited before autosave completes.

## Proposed Technical Approach

- Frontend: React with TypeScript.
- Backend: FastAPI with Python.
- Database: SQLite behind repositories/services that can later target
  PostgreSQL.
- Files: managed local storage behind a storage interface that can later target
  object storage.
- Generation: deterministic templates, typed profile fields, conditional
  sections, and approved reusable content blocks.
- Autosave routine edits; require confirmation for consequential actions such
  as issue, approve, delete, restore, and framework migration.
- Build one tested vertical slice at a time.

## Major Decisions

### Decision 001: Project Is the Engagement Boundary

**Decision:** Profiles, assessments, evidence context, remediation, and outputs
belong to a client project.

**Why:** The same client can run different frameworks or annual efforts with
different environments and scope.

**Alternatives:** One global client profile or completely disconnected records.

**Tradeoff:** Shared client facts may initially be repeated across projects.

**How difficult it would be to change later:** Moderate; shared organization
facts can be extracted after actual reuse patterns are known.

### Decision 002: Local-First but Migration-Aware

**Decision:** V1 uses SQLite and managed local files while isolating persistence
behind interfaces.

**Why:** It keeps V1 simple and offline while preserving a path to hosted
PostgreSQL and object storage.

**Alternatives:** Host immediately or build a desktop-native application.

**Tradeoff:** V2 still requires migration and security engineering.

**How difficult it would be to change later:** Moderate if interfaces and stable
IDs are maintained; high if storage concerns leak into UI code.

### Decision 003: Assessments Are Snapshots; Remediation Is Continuous

**Decision:** Issued assessments are immutable snapshots. Findings, POA&M, and
recurring work continue at project level across assessments.

**Why:** Historical reports must remain reproducible while remediation continues.

**Alternatives:** Duplicate all work into each reassessment or mutate prior
assessments.

**Tradeoff:** The UI must clearly distinguish assessment state from current
project state.

**How difficult it would be to change later:** High because it affects most data
relationships.

### Decision 004: Shared Engines, Framework-Specific Workflows

**Decision:** CMMC and HIPAA share evidence, risk, action, audit, and reporting
engines but retain separate catalogs and guided assessment workflows.

**Why:** Reuse should not imply that different frameworks are equivalent.

**Alternatives:** Separate applications or a premature universal control model.

**Tradeoff:** Some framework-specific behavior remains intentionally duplicated.

**How difficult it would be to change later:** Low to moderate; crosswalking can
be added as an explicit layer in V2.

### Decision 005: Deterministic Generation Before AI

**Decision:** Policies and documents use typed fields, named tokens, conditional
sections, and approved reusable text in V1.

**Why:** Outputs remain predictable, reviewable, and offline.

**Alternatives:** Call an LLM now or rely on manual copy/paste.

**Tradeoff:** Templates require deliberate setup and cannot improvise missing
content.

**How difficult it would be to change later:** Low; LLM assistance can be added
to bounded drafting steps without replacing source data.

### Decision 006: Prototype Before Production UI

**Decision:** Build three structurally different throwaway UI variants and
select the interaction model before production implementation.

**Why:** The previous platform failed primarily in navigation, density, and
workflow coherence.

**Alternatives:** Design directly in production or use static screenshots only.

**Tradeoff:** Prototype code is discarded and rebuilt after decisions are
captured.

**How difficult it would be to change later:** Low now and expensive after the
production shell is established.

## Acceptance Criteria

- AC-001: A user can create a client and framework project, complete onboarding,
  close the app, reopen it, and continue with saved profile data.
- AC-002: A CMMC project supports all 110 Level 2 requirements and 320 assessment
  objectives for its pinned framework version.
- AC-003: A HIPAA project exposes Security, Privacy, Breach Notification, and
  Security Risk Analysis work areas.
- AC-004: Met cannot be finalized without evidence or an interview/observation
  record.
- AC-005: Not Met and Pending work can produce traceable findings and continuous
  project-level remediation.
- AC-006: A reassessment copies prior state as Needs Revalidation without
  modifying the issued source assessment or duplicating evidence files.
- AC-007: One evidence artifact can support multiple requirements while each
  mapping retains its own rationale and lifecycle.
- AC-008: The 5x5 engine calculates inherent and residual risk consistently and
  enforces HIPAA scope-completeness rules before issue.
- AC-009: A policy can be generated from project fields, edited, approved,
  reviewed with no change, and superseded with complete history.
- AC-010: Recurring reviews appear at their configured lead time and create a
  durable review record.
- AC-011: Reports reproduce the source profile, assessment, framework, and
  evidence state captured at issue time.
- AC-012: Every governed change is attributed to the selected Johnathan account.
- AC-013: Automatic backup retention keeps no more than 14 daily and 2 weekly
  backups, and a verified restore recovers a test workspace.
- AC-014: Core workflows run offline on supported Windows ARM64 and x64 systems.
- AC-015: The approved UI prototype decisions are documented before production
  UI implementation begins.

## Success Criteria

- Johnathan can complete a real CMMC or HIPAA engagement without maintaining a
  second authoritative tracker.
- The next required action is obvious from both global and project views.
- Every issued conclusion can be traced to its framework version, profile
  snapshot, evidence, reviewer, and remediation state.
- Reassessment reuses prior work without silently treating old evidence as
  current.
- Reports and policy drafts require review but not repetitive re-entry of known
  project facts.

## Open Questions

- Final source and licensing approach for the HIPAA catalog and guidance content.
- Final RainTech policy, procedure, report, and SSP templates.
- Exact production styling and interaction model, to be resolved by the UI
  prototype.

## Approval

Approved by Johnathan on July 23, 2026. This approval authorizes the UI prototype
and creation of the vertical-slice ticket plan. Each production slice still
requires an approved ticket and applicable verification.
