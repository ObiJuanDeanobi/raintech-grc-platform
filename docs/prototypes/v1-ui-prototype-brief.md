# V1 UI Prototype Brief

## Status

Approved for prototype implementation on July 23, 2026.

## Design Question

What navigation and information hierarchy make a dense CMMC/HIPAA delivery
workspace feel clear enough for one person to operate daily?

## Prototype Shape

- Build three structurally different variants on one throwaway route.
- Switch variants through `?variant=A`, `?variant=B`, and `?variant=C`.
- Provide a floating variant switcher and left/right keyboard navigation.
- Use in-memory synthetic fixtures only.
- Keep the prototype read-only except for harmless local interaction state.
- Do not connect the prototype to the production database or mutations.

## Shared Synthetic Scenarios

### CMMC Scenario

- Client: synthetic defense contractor.
- Project: `CMMC Level 2 2026`.
- Partially complete profile with current and target environments.
- Requirements in Blank, Met, Not Met, and Pending states.
- Open POA&M work, evidence mappings, risks, recurring reviews, and a preliminary
  implementation estimate.

### HIPAA Scenario

- Client: synthetic Federally Qualified Health Center.
- Project: `HIPAA 2026`.
- Security, Privacy, Breach Notification, and SRA work in progress.
- Addressable decisions, an N/A rationale, shared evidence, corrective actions,
  a 5x5 risk, and an upcoming recurring review.

## Required Surfaces

Each variant must make these workflows judgeable:

- global client/project selection
- project Overview and next-action clarity
- progressive current/target project profile
- CMMC requirement-centered gap analysis with objectives
- HIPAA four-area assessment navigation
- unified action queue with record-type distinction
- evidence reuse and mapping context
- 5x5 inherent/residual risk view
- policy lifecycle and recurring reviews
- reports and issue readiness

## Variant A - Project Command Center

Persistent left navigation with a compact project header and action-oriented
Overview. Gap-analysis work uses a dense center table with a right-side details
inspector.

Question answered: does a conventional operational workspace provide the best
speed and orientation?

## Variant B - Guided Engagement Flow

Project phase rail across the top with the current workflow emphasized:
Onboarding, Scope, Gap Analysis, Remediation, Validation, and Reporting.
Navigation inside each phase exposes overlapping work without pretending phases
are strictly sequential.

Question answered: does phase guidance make complex engagements easier to
operate without hiding continuous remediation?

## Variant C - Work Queue First

The global action queue is the home surface. Selecting work opens the relevant
project and requirement context in a split workspace, while project navigation
remains available as a secondary path.

Question answered: is the next-action model more useful for daily operation than
starting from a client or project dashboard?

## Visual Constraints

- Quiet, work-focused, and optimized for scanning.
- No marketing hero, decorative dashboard cards, nested cards, or oversized
  headings.
- Stable dense tables, split panes, tabs, filters, and clear status indicators.
- Use icons for familiar tool actions and text for consequential commands.
- Avoid a one-note blue, purple, beige, or dark-slate palette.
- Verify desktop and laptop layouts; the conference/customer mobile experience
  is not part of this prototype.

## Review Prompts

- Can Johnathan always tell which client, project, framework, and assessment is
  active?
- Is the next useful action obvious?
- Can profile facts be corrected without leaving the work context?
- Are assessment status, evidence support, findings, and remediation visibly
  connected without collapsing into one record?
- Does HIPAA feel purpose-built rather than renamed CMMC?
- Can recurring reviews and stale evidence be found before they become overdue?
- Which variant has the best shell, assessment workspace, and action model?

## Prototype Exit Criteria

- All three variants run from one command.
- Variant selection persists in the URL.
- Both synthetic projects are available in every variant.
- Required surfaces are represented at realistic information density.
- Desktop/laptop screenshots are captured for each variant.
- The selected elements and rejected tradeoffs are documented.
- Prototype code remains clearly experimental and is not promoted directly into
  production.
