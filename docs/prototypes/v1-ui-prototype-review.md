# V1 UI Prototype Review

## Status

Experimental prototype complete on `codex/v1-ui-prototype`. Interaction-model
selection is pending Johnathan's review. Prototype code must not be promoted
directly into production.

## Run

```powershell
cd prototypes\v1-project-workspace
.\run.ps1
```

Open `http://127.0.0.1:5173/?variant=A`. Use the bottom switcher or left/right
arrow keys. Switch between the synthetic CMMC and FQHC HIPAA projects from the
project selector.

## Comparison Checklist

### A — Project Command Center

- Is the persistent project navigation the fastest way to stay oriented?
- Does the dense assessment table plus context inspector show enough linkage?
- Is project-level work too dominant compared with cross-project priorities?

### B — Guided Engagement Flow

- Does the phase rail clarify the engagement without implying strict sequence?
- Is parallel remediation visible enough while gap analysis is in focus?
- Does phase guidance add useful structure or consume too much vertical space?

### C — Work Queue First

- Is starting from the unified queue the best daily operating model?
- Does the split context preserve enough client, project, and assessment identity?
- Is secondary project navigation discoverable enough for non-queue work?

## Selection Record

Initial direction selected by Johnathan:

- **Base shell:** Variant A, Project Command Center.
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
  signed-in user without competing with project identity.
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
- **Rejected tradeoff from C:** do not make the cross-project queue the default
  home; it weakens project orientation for deep assessment work.

This is an interaction-model decision, not approval to promote prototype code.
The production shell must be implemented afresh under a production ticket.

Production implementation requires a new approved ticket and a fresh,
tested implementation rather than promotion of this prototype code.

## Visual Verification

Screenshots were captured at 1440×900 (desktop, CMMC) and 1280×720 (laptop,
HIPAA) for every variant under
`prototypes/v1-project-workspace/screenshots/`.

Checks completed:

- no horizontal page overflow
- no overlapping structural panes
- no blank critical content
- labels and primary text remain readable
- project and variant controls work
- URL variant state survives reload
- browser console contains no errors or warnings
