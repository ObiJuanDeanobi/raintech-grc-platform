# RainTech CMMC GRC Platform Roadmap

## Product Spine

Build the platform around one clean flow:

```text
Profile -> Scope/Quote -> Gap Analysis -> Evidence -> Reports -> Documents
```

The customer profile is progressive. V1 creates an initial scoping profile. V2 enriches that profile during gap analysis. Formal documents are generated from the final implementation profile, not from intake alone.

## Urgent Milestones

### V1 - Profile, Quote, Readiness

Goal: create a clean internal/customer-facing intake flow that produces an initial profile, readiness score, quote range, confidence level, and recommended package.

Acceptance:

- Each intake question maps to score, quote, implementation path, profile, evidence guidance, or document generation.
- Initial profile is saved locally.
- Readiness scoring is deterministic and testable.
- Quote recommendation uses RainTech package/pricing rules.
- Summary page clearly shows score, package, quote range, confidence, and next steps.

### V2 - Internal Workspace and Gap Analysis

Goal: create the internal compliance workspace where RainTech can review customers, edit profiles, and complete CMMC gap analysis.

Acceptance:

- Customer workspace shows profile, quote/readiness, assessment status, notes, and next actions.
- Gap analysis supports CMMC Level 2 objectives and status tracking.
- Gap analysis enriches the implementation profile.
- POA&M candidates can be flagged during assessment.
- Final implementation profile is distinguishable from the initial intake profile.

### V3 - Evidence Capture

Goal: integrate the existing CMMC evidence tracker capabilities into the customer workspace.

Acceptance:

- Evidence can be uploaded by file picker and drag/drop.
- Evidence is stored once and mapped to one or many objectives.
- Evidence can be reused across objectives.
- Replace evidence keeps mappings intact.
- Delete evidence clears mappings cleanly.
- ZIP export produces objective-specific evidence copies and a manifest.

### V4 - Reports

Goal: produce useful internal and client-ready reporting from profile, gap, POA&M, and evidence data.

Acceptance:

- Readiness report is exportable.
- Gap analysis report is exportable.
- POA&M/status report is exportable.
- Evidence capture report is exportable.
- Reports use customer/profile/assessment data instead of static text.

### V5 - Documents

Goal: generate SSP, policies, procedures, and diagrams from templates using the final implementation profile.

Acceptance:

- Template registry supports RainTech-provided templates.
- SSP generation uses implementation profile, control status, and evidence data.
- Policies/procedures are generated as editable drafts.
- Diagrams are generated from profile data and remain reviewable before export.
- Generated documents are linked back to the customer.

## Planned But Not Urgent

### V6 - Hosted Platform and RBAC

Move from local-first internal use to hosted deployment with proper authentication, tenant separation, audit logging, RBAC, backup, and secure file handling.

### V7 - Customer Portal

Add a customer-facing portal for report viewing, evidence requests, limited profile updates, and task collaboration.

### V8 - Automated Evidence

Build evidence collection pipelines for common sources such as Microsoft 365, Entra ID, Intune, Defender, Huntress, Autotask, and SharePoint.

## Project Rules

- CMMC Level 2 only until V1-V5 are solid.
- Build vertical slices, not giant horizontal layers.
- Keep the data model explicit and boring.
- No intake question survives unless it drives scope, score, quote, evidence, reports, or documents.
- Local-first remains the default until the hosted milestone.
- Reports come before document generation.
- Customer portal is deferred until internal workflows are reliable.
