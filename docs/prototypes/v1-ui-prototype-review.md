# V1 UI Prototype Review

## Status

Experimental prototype complete on `codex/v1-ui-prototype`. The selected
interaction model is recorded below. Prototype code must not be promoted
directly into production.

## Run

```powershell
cd prototypes\v1-project-workspace
.\run.ps1
```

Open `http://127.0.0.1:5173/`. Use Dashboard for cross-client work, or select a
synthetic CMMC or FQHC HIPAA client from the left sidebar.

## Review Checklist

- Does Dashboard provide a clear global home above the client list?
- Does Unified Queue clearly mean work across all clients?
- Does Client Queue clearly mean work scoped to the selected client?
- Does the assessment workspace keep guidance central and the working record
  visible without excessive context switching?

## Selection Record

Initial direction selected by Johnathan:

- **Base shell:** Variant A, Project Command Center. Variants B and C and the
  prototype switcher were removed after selection.
- **Scope hierarchy:** Dashboard is the global home above client profiles in
  the sidebar. Dashboard owns Unified Queue across all clients; each selected
  client Overview owns a Client Queue.
- **Project schedule:** project end date is required during onboarding/profile
  setup and is surfaced in the client list, selected project identity, and
  global portfolio summary. Dashboard shows Active Projects above Unified
  Queue with project name, end date, and days remaining. Client pages replace
  the redundant due-soon metric with a prominent Project Ends metric.
- **Assessment workspace:** retain A's dense requirement list and right-side
  inspector concept, but move it out of Overview and into a dedicated
  objective-by-objective assessment workspace.
- **Overview additions from B:** add a compact engagement-phase rail and a
  "continue where you left off" panel showing assessment progress,
  implementation context, evidence support, and the linked action.
- **Action model:** retain A's project Overview and direct navigation, with the
  unified queue available as a deliberate secondary destination.
- **Overview boundary:** remove the requirement-review list and requirement
  inspector. Overview contains only project orientation, resumption context,
  and the unified actionable-work queue directly below it. Evidence, risk, and
  report blockers enter that queue rather than appearing in a separate summary
  strip.
- **Global utility context:** add a compact top bar for notifications and the
  signed-in user without competing with project identity; do not duplicate the
  signed-in name in each project header.
- **Assessment interaction:** selecting `Assessments` opens an objective
  navigator, a central decision surface with requirement text, what to
  determine, implementation guidance, expected evidence, linked work, and the
  determination state, plus a right-side working record containing the
  implementation statement, mapped evidence, and assessment notes.
- **Overview visualization:** do not add a separate chart section. The existing
  metrics and progress treatment provide sufficient orientation; the unified
  queue expands with realistic evidence, risk, and report-blocker work instead.
- **Rejected tradeoff from B:** do not make the entire workspace phase-first;
  the full phase shell consumes vertical space and can overstate sequentiality.
- **Qualified lesson from C:** retain a cross-client queue on the global
  Dashboard, while keeping client orientation for deep assessment work.

This is an interaction-model decision, not approval to promote prototype code.
The production shell must be implemented afresh under a production ticket.

Production implementation requires a new approved ticket and a fresh,
tested implementation rather than promotion of this prototype code.

## Visual Verification

Screenshots were captured at 1440×900 (desktop, CMMC) and 1280×720 (laptop,
HIPAA) for the selected workspace under
`prototypes/v1-project-workspace/screenshots/`.

Checks completed:

- no horizontal page overflow
- no overlapping structural panes
- no blank critical content
- labels and primary text remain readable
- Dashboard, client selection, and assessment controls work
- browser console contains no errors or warnings
