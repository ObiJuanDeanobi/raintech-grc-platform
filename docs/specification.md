# RainTech GRC Platform Specification

## Status

Approved. Originally approved July 23, 2026; the post-prototype revision, the
catalog count correction and the bare-standard correction approved July 27, 2026;
the Breach paragraph correction approved July 28, 2026.

No unapproved changes are outstanding. Production BUILD is unblocked. Each slice
still requires an approved ticket and applicable verification, and changing this
document again requires Johnathan's approval.

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
- The assessable unit differs by framework, because the two frameworks are
  decomposed by different authorities to different depths. Do not force one shape
  onto both.
  - **CMMC:** determinations are recorded at assessment-objective level, because
    NIST SP 800-171A normatively decomposes each requirement into determination
    statements. Requirement status derives from its objectives.
  - **HIPAA:** determinations are recorded at implementation-specification level,
    or at the standard itself where a standard has no implementation
    specifications. Four published paragraphs carry distinct obligations under
    neither label and are independently assessable: 164.412(a), 164.412(b),
    164.414(a), and 164.414(b). Standard status derives from its specifications.
    No objective layer is created — 45 CFR Part 164 publishes no such
    decomposition, and inventing one would produce assessable records that cannot
    be cited.
  - Published subordinate CFR paragraphs beneath a HIPAA record do not become
    separate determination-bearing records. The record retains its lead
    regulation text; its subordinate paragraphs are displayed beneath it as
    individually cited, non-determinative guidance entries. Each entry has one
    presentation role: `assessment_check` for an operative requirement,
    `applicability_note` for an exception, exemption, or N/A condition, or
    `context` for a structural lead-in or optional permission. Only
    `assessment_check` renders a checkbox. The complete official context is the
    parent text plus those nested paragraphs. Do not duplicate all child text
    into the parent record, and do not promote those children into separate
    assessment results.
  - The OCR Audit Protocol's key activities and audit inquiries populate the
    implementation guidance and expected evidence fields. They are not records
    that carry a determination.
- The three HIPAA rules are not structurally uniform, but they diverge on the
  Required/Addressable designation rather than on the standard-and-implementation-
  specification model itself. Do not treat the Privacy Rule as standard-only; that
  would drop most of its assessable records.
  - **Security Rule (Subpart C, 45 CFR 164.302-318):** standards with Required and
    Addressable implementation specifications. The Addressable designation exists
    only here, per 45 CFR 164.306(d).
  - **Privacy Rule (Subpart E, 45 CFR 164.500-535):** uses the standard-and-
    implementation-specification model extensively — more heavily than the Security
    Rule — but carries no Required or Addressable designation on any specification.
  - **Breach Notification Rule (Subpart D, 45 CFR 164.400-414):** four standards
    and nine implementation specifications. Structurally it follows the same
    shape as the other two rules, not a different one. Its standards are written
    as a bare `Standard` rather than `Standard: <name>`, taking their subject
    from the section heading — 164.404(a), .406(a), .408(a) and .410(a). The
    same bare form appears once in the Privacy Rule, at 164.502(a).
  - Two provisions, 45 CFR 164.412 and 164.414, carry obligations under no
    standard or implementation-specification label. Their four top-level
    paragraphs are published, independently citable obligations and are the
    assessable units: 164.412(a), 164.412(b), 164.414(a), and 164.414(b). This is
    the documented exception across the whole catalog, four records of 194, not
    an invented objective layer or a parallel model for any rule.
  - Authoritative record counts, established by ingestion on July 27, 2026 and
    asserted by the catalog tests:

    | Catalog area | Standards | Implementation specifications | Paragraphs | Sections | Required | Addressable |
    |---|---:|---:|---:|---:|---:|---:|
    | Security Rule (Subpart C) | 22 | 41 | 0 | 0 | 19 | 22 |
    | Privacy Rule (Subpart E) | 56 | 58 | 0 | 0 | 0 | 0 |
    | Breach Rule (Subpart D) | 4 | 9 | 4 | 0 | 0 | 0 |

    Source: eCFR Title 45 Part 164, snapshot 2026-07-01, retrieved July 27, 2026
    via the eCFR versioner API. Pinned as framework version
    `hipaa-45cfr164-2026-07-01`; see `catalog/README.md`.

    Corrected twice. The counts first recorded here were indicative and two were
    wrong. The first correction, on ingestion, was itself incomplete: it repeated
    the claim that Subpart D publishes no standards. Practitioner review found
    that wrong — Subpart D publishes four, written as a bare `Standard`, and the
    same form appears at 164.502(a), the Privacy Rule's general prohibition on
    use and disclosure. Recognising only `Standard: <name>` had lost all five,
    and had left the Breach Notification Rule modelled as bare sections rather
    than as standards with specifications beneath them.
  - One catalog record shape must tolerate all three, carrying `addressable` only
    where the regulation actually uses it — which is Subpart C alone.
- The Security Risk Analysis is a workflow area, not a catalog area. Risk analysis
  is 45 CFR 164.308(a)(1)(ii)(A), a single Required implementation specification
  inside the Security Management Process standard at 164.308(a)(1)(i). It is
  already a Security Rule catalog record and must not be ingested a second time as
  a fourth catalog area. HIPAA projects therefore present four work areas over
  three catalog areas.
- Requirement or standard status is derived and is not edited directly:
  - all children Met, or Met with a documented N/A where the framework allows it,
    derives Met
  - any child Not Met derives Not Met
  - otherwise, any child Pending derives Pending
  - otherwise the parent remains Blank
  - Not Met takes precedence over Pending when both are present
- Only the derived requirement status feeds official CMMC scoring. Objective-level
  status is never scored on its own.
- Confirmed by Johnathan on July 27, 2026. The CMMC rule follows the structure of
  NIST SP 800-171A, where a requirement is satisfied only when all of its
  determination statements are satisfied.
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

Work-item state transitions:

- Draft to Open on first assignment. Open, In Progress, and Waiting move freely
  between one another as work proceeds.
- Any of Open, In Progress, or Waiting moves to Ready for Validation when the
  responsible party asserts the work is done.
- Ready for Validation moves to Closed only through an explicit validation
  decision recorded by the selected account. Nothing reaches Closed by any other
  path, and no item closes as a side effect of another item closing.
- Failed validation returns the item to In Progress, or creates a linked
  successor when the original approach was abandoned.
- Withdrawn is reachable from any open state and is exceptional. It records that
  the item should not have existed, which is different from Closed.
- Closed and Withdrawn are terminal. Reopening creates a linked successor rather
  than reviving a terminal record.
- A finding is closed only by revalidation of the underlying requirement or
  standard in a later assessment. Completing or closing its linked POA&M item or
  corrective action never closes the finding.

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
- Templates, approved content blocks, and generated deliverables must satisfy the
  output language constraints in ADR 0011: no certification claims for RainTech,
  the platform, or a client system; no asserted regulatory frequency the
  controlling authority does not mandate; no presentation of evidence reuse as
  framework equivalence; and no internal progress percentage presented as a
  compliance conclusion. An approved content block is reviewed against ADR 0011
  before it becomes reusable.
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

## Accepted Interaction Model

Selected through the UI prototype on `codex/v1-ui-prototype` and recorded in
`docs/prototypes/v1-ui-prototype-review.md`. Production reimplements this model
against the real architecture; prototype code is not promoted.

**Two scopes.** Dashboard is the cross-client home and sits above the client list
in the sidebar. Selecting a client opens that project's workspace. The two are
never blended.

- Dashboard owns the **Unified Queue**, which spans every client, and Active
  Projects above it as a stacked list showing client, project, phase, end date,
  days remaining, and project-completion percentage.
- Each client Overview owns the **Client Queue**, scoped to the selected client.
- Project completion measures delivery progress and is distinct from profile
  completeness. Neither is a compliance conclusion and neither appears in
  client-facing output.

**Overview is orientation, not assessment.** It contains a compact phase rail, a
work-resumption panel, and the Client Queue directly beneath. It does not contain
a requirement-review list, a requirement inspector, a separate evidence/risk/report
summary strip, or a chart section added to fill space.

**Assessments is objective-by-objective.** An objective navigator on the left, a
central decision surface carrying the requirement, what to determine, the
determination control, implementation guidance, expected evidence, and linked
work, and a right-side working record holding the implementation statement,
mapped evidence, and assessment notes.

**Profile is progressive and additive.** The onboarding baseline stays visible
beside the current validated state and the required target, each fact carrying a
status of Confirmed, Changed, or Missing plus its assessment impact. Assessment
findings enrich the Implementation Profile; they never overwrite the onboarding
baseline.

**Queues project; Actions/POA&M owns the records.** The queues are prioritized
projections for deciding what to work on. Actions/POA&M is where the records are
managed, and each record exposes what a queue row cannot: the record type, who
raised it, its links in both directions, its next action, and the condition that
must be true before it closes. Record types stay distinct rather than flattening
into one row shape, and differ by framework on the shared surface — CMMC shows
POA&M, HIPAA shows Corrective action. Ready for Validation is a prominent group,
not a separate destination, because those items require an explicit decision.
Report blockers and stale-evidence warnings are derived signals that appear in the
queues; they are not records and are not managed here.

**Global utility context.** A compact top bar carries notifications and the
signed-in account. The signed-in name is not repeated in each project header.

**Project end date** is captured during onboarding as a profile field and stays
visible in the client list, project identity, Profile, and Dashboard.

Rejected during prototyping: a phase-first workspace shell, which overstates
sequentiality and consumes vertical space; and the global queue as the default
home, which weakens project orientation for deep assessment work.

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
  Narrowed by GitHub issue #21: eCFR, the OCR Audit Protocol, and NIST SP 800-66
  Rev. 2 are all US government works, so no licensing spend is expected. The HHS
  SRA Tool remains unassessed and its terms must be checked before any reuse.
- Final RainTech policy, procedure, report, and SSP templates.

Closed:

- Exact production styling and interaction model. Resolved by the UI prototype and
  recorded in the Accepted Interaction Model section. Closed July 27, 2026.

## Approval

Approved by Johnathan on July 23, 2026. This approval authorized the UI prototype
and creation of the vertical-slice ticket plan. Each production slice still
requires an approved ticket and applicable verification.

### Post-prototype revision — approved July 27, 2026

The Accepted Interaction Model, both rollup rules, the work-item state transitions,
the HIPAA rule-structure correction, and the ADR 0011 reference were added after
the July 23 approval. **Approved as a whole by Johnathan on July 27, 2026.**
Production BUILD is unblocked; GitHub issue #21 is the first ticket.

### Bare-standard correction — approved July 27, 2026

Practitioner review of the ingested catalog found that the specification, and
the ingestion built from it, recognised only standards written
`Standard: <name>`. Five standards are written as a bare `Standard` taking their
subject from the section heading: 45 CFR 164.502(a), and all four Breach
Notification Rule standards at 164.404(a), .406(a), .408(a) and .410(a). All
five were absent from the catalog, and the Breach Notification Rule was modelled
as section-level records rather than as standards with implementation
specifications beneath them.

All three rules now share one primary shape. At this revision, 164.412 and
164.414 were represented as the two section-level exceptions and records went
191 to 192. Practitioner review later replaced those incomplete fallbacks with
four paragraph records, as recorded below. **Approved by Johnathan on July 27,
2026.**

### Catalog count correction — approved July 27, 2026

The indicative HIPAA record counts under Frameworks and Assessments were replaced
with the authoritative counts established by catalog ingestion (GitHub issue #21,
framework version `hipaa-45cfr164-2026-07-01`). Two of the indicative numbers were
wrong: Subpart D was described as publishing no implementation specifications when
it publishes nine, and Subpart E was recorded as 56 standards and roughly 77
specification references rather than 55 and 58. The indicative counts were
explicitly provisional and the section said ingestion would establish the
authoritative figures. **Approved by Johnathan on July 27, 2026.**

### Breach paragraph correction — approved July 28, 2026

Practitioner review found that the two section-level fallback records at
164.412 and 164.414 did not preserve the complete assessable text. The 164.412
record contained only the introductory clause and omitted its written and oral
law-enforcement-delay procedures. The 164.414 record contained its
administrative-requirements paragraph but omitted the separate burden-of-proof
obligation.

The two section records are replaced by four published paragraph records:
164.412(a), 164.412(b), 164.414(a), and 164.414(b). These are CFR citations, not
invented objectives. Records go 192 to 194; Breach Notification records go 15
to 17. **Approved by Johnathan on July 28, 2026.**

### Subordinate paragraph presentation — approved July 28, 2026

Source reconciliation found 731 published child paragraphs beneath 84 HIPAA
catalog records. Many parent texts are lead-ins whose operative detail is in
those children. They remain under their existing parent record and are
presented as individually cited, non-determinative prompts under issue #29.

The catalog remains at 194 determination-bearing records. Child paragraphs do
not carry status, produce findings, or appear as separate assessment results.
The parent record text is not expanded to duplicate all child text; the complete
official context is presented as the parent lead plus its nested cited
paragraphs. **Approved by Johnathan on July 28, 2026.**

### Privacy prompt filter — approved July 28, 2026

Privacy Rule child paragraphs are not all checklist questions. Each cited entry
is classified for presentation:

- `assessment_check`: an operative `must`, `shall`, or conditional requirement;
  renders a checkbox.
- `applicability_note`: an exception, exemption, “not required” provision, or
  other scope/N/A condition; visible for applicability reasoning without a
  checkbox.
- `context`: a structural lead-in such as “must contain:” or an optional
  permission; displayed as a heading or guidance without a checkbox.

Conditional obligations remain assessment checks when their condition applies.
No role carries its own determination or produces a finding. This replaces the
spike's raw behavior of rendering every extracted Privacy subparagraph as a
checkbox. **Approved by Johnathan on July 28, 2026.**

Settled in this revision:

- CMMC objective-to-requirement rollup confirmed by Johnathan, July 27, 2026.
- HIPAA determinations recorded at implementation-specification level, with no
  invented objective layer. Confirmed July 27, 2026.
- HIPAA subordinate CFR paragraphs remain cited, non-determinative prompts
  beneath their parent record rather than duplicated into parent text or
  promoted to assessment results. Confirmed July 28, 2026.
- Privacy Rule child paragraphs use the three presentation roles
  `assessment_check`, `applicability_note`, and `context`; only the first renders
  a checkbox. Confirmed July 28, 2026.
- First engagement is a full HIPAA program assessment within weeks. Slice 4
  precedes Slice 3. The platform runs in parallel with existing methods rather
  than on the critical path of live client work. `ROADMAP.md` now records that
  ordering, so it is no longer an open question.
- HIPAA rule structure corrected against primary source, July 27, 2026. The
  earlier claim that the Privacy Rule "largely does not use that model" was wrong:
  Subpart E uses standards and implementation specifications more heavily than
  Subpart C does, and what it lacks is the Required/Addressable designation. The
  correction is recorded under Frameworks and Assessments with its citation and
  retrieval date. Verified against eCFR rather than asserted.
- The Security Risk Analysis is a workflow area, not a catalog area. It is already
  a Security Rule record at 45 CFR 164.308(a)(1)(ii)(A).

Deferred, not blocking:

- Whether to restructure `ROADMAP.md` so the required and optional halves of
  Slices 2, 5, and 7 are separated. That narrows V1 and is a scope change. It does
  not gate the HIPAA catalog work and is deferred until after the first
  engagement, when the required half is known rather than predicted.
