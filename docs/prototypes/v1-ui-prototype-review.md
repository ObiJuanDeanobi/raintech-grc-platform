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

After review, record:

- selected shell
- selected assessment workspace
- selected action model
- elements borrowed from another variant
- rejected tradeoffs and why

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
