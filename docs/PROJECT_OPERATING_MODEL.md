# Project Operating Model

## Core Data Objects

These concepts should remain explicit in the code and issue tracker:

- Customer
- InitialProfile
- ImplementationProfile
- ReadinessScore
- QuoteRecommendation
- GapAssessment
- ControlObjectiveResult
- EvidenceItem
- EvidenceMapping
- POAMItem
- Report
- GeneratedDocument

## Initial Profile vs Implementation Profile

The V1 intake creates an InitialProfile. It is allowed to be incomplete because it supports sales scoping, readiness scoring, and quoting.

The V2 gap analysis enriches the profile into an ImplementationProfile. This is the authoritative environment profile used for SSPs, policies, procedures, diagrams, evidence guidance, and later automation.

## Question Justification Rule

Every customer-facing intake question must support at least one of:

- readiness score
- quote range
- recommended implementation path
- implementation profile
- evidence capture guidance
- SSP/policy/procedure/diagram generation

Questions that do not support one of those outcomes should be removed.

## Vertical Slice Rule

Prefer complete, testable workflows over disconnected screens. The first complete slice is:

```text
Create customer -> complete initial profile -> calculate score and quote -> save record -> view summary
```

Future slices should attach to this flow instead of creating separate mini-apps.

## Issue Acceptance Criteria

Each GitHub issue should include:

- outcome
- data objects touched
- acceptance criteria
- verification steps
- screenshots required when UI changes

## Verification Defaults

For the current local app foundation, keep these checks handy:

- `python -m pytest -q`
- seed counts: 14 domains, 110 requirements, 320 objectives
- live checks for `/`, `/objectives`, `/evidence`, `/reports/completion`, and `/exports/zip`
