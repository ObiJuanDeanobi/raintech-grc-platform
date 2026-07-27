# Project Status

## Current phase

Production build, Slice 4a

## Current mode

Build

## Current objective

Ingest and version the HIPAA full-program catalog so it can be reviewed on paper
before any HIPAA assessment surface is built.

## Approved specification

`docs/specification.md`. Approved July 23, 2026; post-prototype revision approved
July 27, 2026. No unapproved changes outstanding.

## Active ticket

GitHub issue #21: Slice 4a, ingest and version the HIPAA full-program catalog.

GitHub issue #20 (UI prototype) is complete and can be closed. Three of its
acceptance criteria — the three-variant switcher, left/right variant controls, and
per-variant screenshots — were superseded when the prototype collapsed to the
selected Variant A. That is recorded in `docs/prototypes/v1-ui-prototype-review.md`.

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
- Post-prototype specification revision approved by Johnathan, July 27, 2026.
  Production BUILD is unblocked.
- Stale open question on production styling closed; it was resolved by the
  prototype.
- `chore/agent-workflow-hardening` deleted after confirming it was fully merged
  into `main`.

## In progress

- GitHub issue #21: HIPAA full-program catalog ingestion.

## Blocked

- Nothing. The specification approval that gated production BUILD landed
  July 27, 2026.

## Known risks

- The HIPAA catalog is unbuilt and the first engagement is weeks away. The
  platform runs in parallel with the existing method and is not on the critical
  path of client work.
- The OCR Audit Protocol predates the current rule text and must be reconciled
  against eCFR during ingestion rather than assumed current.
- HHS SRA Tool terms are unassessed. No content from it may be reused until they
  are checked.
- Document templates remain an open input.
- The local `data/` folder contains legacy evidence and exports that must be
  preserved until a separate backup/retention decision is made.
- Launcher, offline operation, packaging, and backup/restore cannot be verified
  from a cloud session. Those belong to Slices 1 and 7 on the Windows machine.

## Next recommended action

Build GitHub issue #21 from clean `main` without promoting prototype code:
an ingestion script over eCFR Title 45 Part 164, a versioned catalog fixture, a
structure and count test, and a readable export for practitioner review.

The required/optional split of Slices 2, 5, and 7 is deferred until after the first
engagement. It is a scope change and it does not gate the HIPAA catalog.
