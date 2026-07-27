# Project Status

## Current phase

Prototype review

## Current mode

Build

## Current objective

Confirm the refined hybrid A interaction model and use the recorded decision to
shape the production workspace ticket.

## Approved specification

`docs/specification.md`, approved July 23, 2026.

## Active ticket

GitHub issue #20: Prototype V1 project workspace UI variants.

## Completed

- Repository AI workflow configured.
- CMMC and HIPAA V1 discovery completed.
- Draft specification, roadmap, operating model, and prototype brief created.
- Specification, roadmap, and prototype brief approved.
- Legacy application and obsolete backlog moved under `legacy/`.
- Tech-debt and bloat review gates added to delivery workflow.
- Three read-only V1 project workspace UI variants built and visually verified
  for GitHub issue #20.
- Initial interaction direction selected: Variant A shell and assessment
  workspace with Variant B's compact phase rail and work-resumption context on
  the Overview.
- Overview refined to project-level orientation only; requirement review and
  contextual guidance now live in a dedicated objective-by-objective
  Assessments workspace.
- Unified actionable work now follows the Overview directly, with redundant
  evidence/risk/report summaries removed and compact notification/user context
  added above the project identity.
- Overview remains chart-free and uses the available space for a fuller unified
  queue; Assessments now centers decision guidance and places implementation,
  evidence, and notes in the right-side working record.
- Selected Variant A was collapsed into a single prototype workspace. Dashboard
  now sits above client profiles and owns the cross-client Unified Queue, while
  each selected client Overview owns its Client Queue; variants B/C and the
  switcher were removed.
- Project end date is now modeled as an onboarding/profile field and surfaced
  in client selection, project identity, and global portfolio orientation.
- Dashboard now places Active Projects above Unified Queue with end dates and
  days remaining; client metric strips emphasize the project end schedule in
  place of redundant due-soon counts.
- Active Projects now uses a stacked list and shows a separate project
  completion percentage and progress bar for each engagement.
- Client Profile now prototypes the progressive profile model: the onboarding
  baseline remains visible beside the enriched implementation state and target,
  with scope counts, schedule, unresolved inputs, assessment impact, and
  downstream consumers shown for synthetic CMMC and HIPAA engagements.

- Actions / POA&M prototyped as a record surface distinct from the two queues,
  with distinct record types, framework-specific vocabulary, an explicit
  Ready for Validation group, and per-record close conditions.
- Agent workflow hardened: CLAUDE.md pointer, CI running prototype typecheck and
  build on every push, UI review rules recorded in AGENTS.md, tech-debt gate text
  deduplicated, test-depth tiers defined, and ADR 0011 added for generated output
  language.
- Prototyping stopped. Coverage matches the next three slices; Evidence, Risks,
  Policies, and Reports are deferred to their own slices rather than prototyped
  months before implementation.
- Specification updated with the accepted interaction model, the
  objective-to-requirement rollup rule, and work-item state transitions.
- HIPAA rule structure verified against eCFR Title 45 Part 164 and corrected. The
  Privacy Rule does use the standard-and-implementation-specification model; only
  the Security Rule carries Required/Addressable. The Security Risk Analysis is a
  workflow area, not a fourth catalog area.
- Roadmap records the build order 1, 2, 4, 3, 5, 6, 7 without renumbering slices.

## In progress

- Specification revision awaiting Johnathan's approval before production BUILD.

## Blocked

- All production BUILD is blocked on one thing: approval of the specification
  revision. The two decisions previously listed here are settled — the rollup rule
  was confirmed July 27, 2026, and the first real engagement is the HIPAA program
  assessment, which fixes the build order at 1, 2, 4, 3, 5, 6, 7.
- GitHub issue #21 (Slice 4a, HIPAA catalog ingestion) is the first ticket to
  start once that approval lands.

## Known risks

- The final HIPAA catalog source and document templates are still open inputs.
- The local `data/` folder contains legacy evidence and exports that must be
  preserved until a separate backup/retention decision is made.

## Next recommended action

Review and approve the specification revision. Then GitHub issue #21 starts, and
production work is reimplemented from clean `main` without promoting prototype
code.

The required/optional split of Slices 2, 5, and 7 is deferred until after the first
engagement. It is a scope change and it does not gate the HIPAA catalog.
