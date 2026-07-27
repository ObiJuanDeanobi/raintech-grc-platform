# RainTech GRC Platform Roadmap

## Product Spine

```text
Client -> Project -> Profile -> Assessment -> Continuous Remediation
       -> Evidence -> Reports/Documents
```

Build complete vertical slices along this spine. Do not recreate the old
platform as a collection of disconnected dashboards.

## Discovery Gate

### UI Prototype

Goal: choose the production interaction model before building the application
shell.

- Create three structurally different, read-only UI variants.
- Use synthetic CMMC and FQHC HIPAA projects.
- Exercise project navigation, profile refinement, CMMC and HIPAA gap analysis,
  continuous actions, evidence, risks, policies, and reports.
- Capture the selected elements and discard prototype code from the production
  branch.

## V1 - Local Internal Delivery Platform

V1 is useful only when it supports a real engagement from onboarding through
issued deliverables.

### Slice 1 - Foundation and Project Workspace

- Local launcher, React/TypeScript UI, FastAPI, SQLite, and managed file storage.
- Johnathan account context and audit attribution.
- Clients, projects, project selection, Overview, autosave, and audit events.
- Framework-version registry and migration-safe stable identifiers.

### Slice 2 - Progressive Profile and CMMC Estimate

- Project-specific onboarding and progressive environment profile.
- Current state, target state, implementation deltas, systems, tools, owners,
  service providers, users, endpoints, and structured information flows.
- CMMC preliminary estimate using editable, versioned pricing rules.
- Internal estimate and customer-facing PDF.
- HIPAA estimate remains manual.

### Slice 4 - HIPAA Program Delivery

**Built before Slice 3.** The first real engagement is a full HIPAA program
assessment. Slice numbers are stable identifiers and are not renumbered; the build
order is 1, 2, 4, 3, 5, 6, 7. Slice 4a — the HIPAA catalog — is the long-lead item
and starts first, because it needs practitioner review time rather than build time.

- Security Rule, Privacy Rule, Breach Notification Rule, and Security Risk
  Analysis work areas.
- Four work areas over three catalog areas. The Security Risk Analysis is a
  workflow surface, not a separate catalog: risk analysis is already a Security
  Rule record at 45 CFR 164.308(a)(1)(ii)(A). Do not ingest it twice.
- Required/addressable decisions and N/A rationale. The Required/Addressable
  designation exists only in the Security Rule (Subpart C), per 45 CFR 164.306(d).
  The Privacy Rule uses standards and implementation specifications heavily but
  carries no such designation. See the specification for the structural detail and
  its citation.
- 5x5 inherent/residual risk analysis with complete ePHI scope checks.
- HIPAA gap, corrective-action, executive, and SRA reports.
- Reassessment by copy and revalidation.

### Slice 3 - CMMC Level 2 Delivery

Built after Slice 4. See the ordering note above.

- Versioned CMMC Level 2 catalog.
- Requirement-centered gap analysis with all assessment objectives.
- Official CMMC scoring only.
- Findings, Pending/Not Met handling, validation, continuous POA&M, and reports.
- Reassessment by copy and revalidation.

### Slice 5 - Evidence and Recurring Reviews

- Upload, reuse, mapping rationale, versioning, replace, detach, recycle bin,
  archive, deduplication, staleness, and manifest export.
- Evidence mappings across requirements and areas within the same project.
- Evidence requests with assignee, due date, notes, next action, and future
  client-collaboration metadata.
- Configurable recurring review schedules and in-app reminders.

### Slice 6 - Policies, Documents, and Reports

- Versioned templates, named fields, conditional sections, and approved content
  blocks.
- Editable drafts, approval, no-change review events, and supersession.
- Browser report preview and applicable PDF, XLSX, DOCX, and ZIP exports.
- Source snapshots and reproducible issued deliverables.

### Slice 7 - Recovery and V1 Hardening

- Configurable backup destination, including RainTech OneDrive.
- Fourteen daily database/configuration backups and two weekly full backups.
- Manual backup, verified restore, and workspace export/import.
- Windows ARM64 and x64 packaging and offline verification.
- End-to-end review against the approved specification.

## V2 - Hosted Collaboration and Extended Modeling

- Hosted PostgreSQL and object storage migration.
- Authentication, RBAC, tenant isolation, and client workspace.
- Public intake only after hosted controls and internal testing are complete.
- Framework crosswalking as an explicit mapping layer.
- Diagram generation from structured project profile and flow data.
- Notifications beyond in-app reminders.

## V3 - Evidence Automation

- Connectors for approved sources such as Microsoft 365, Entra ID, Intune,
  Defender, Huntress, Autotask, and SharePoint.
- Evidence collection schedules, provenance, health monitoring, and exceptions.
- Evaluate bounded LLM assistance only after deterministic workflows and data
  quality are established.

## V4 - Assisted Drafting

- Optional, bounded LLM assistance for narrative drafting and guidance.
- Template and source-data constraints, review gates, and generated-content
  provenance.
- No automated compliance conclusions.

## Project Rules

- CMMC Level 2 and the full HIPAA program are both V1 requirements.
- The project, not the client, is the compliance engagement boundary.
- Profiles begin during onboarding and mature throughout delivery.
- Assessments are immutable issued snapshots; remediation is continuous.
- Evidence reuse never implies framework equivalence.
- No generic readiness score.
- No actual CUI, PHI, or ePHI is stored in V1.
- Core workflows must operate offline.
- Production code begins only after specification and prototype approval.
