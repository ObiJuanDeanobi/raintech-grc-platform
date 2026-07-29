# Project Status

## Current phase

Production build, Slice 4a

## Current mode

Build

## Current objective

Practitioner review of the ingested HIPAA catalog, so the assessable units are
confirmed before any HIPAA assessment surface is built on them.

## Approved specification

`docs/specification.md`. Approved July 23, 2026; post-prototype revision, catalog
count correction and bare-standard correction approved July 27, 2026; Breach
paragraph correction approved July 28, 2026. No unapproved changes outstanding.

## Active ticket

GitHub issue #21: Slice 4a, ingest and version the HIPAA full-program catalog.
The approved four-paragraph Breach correction merged in PR #35. Johnathan's
practitioner review of `docs/catalogs/hipaa-45cfr164-2026-07-01.md` remains the
outstanding acceptance criterion, so the issue stays open.

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
- HIPAA full-program catalog ingested and pinned as framework version
  `hipaa-45cfr164-2026-07-01`: initially 190 assessable records over three
  catalog areas, stable citation-based identifiers, a readable export, and CI
  that rebuilds the catalog from its pinned source and fails on any difference.
- Specification catalog counts replaced with the authoritative figures established
  by ingestion. Two indicative counts were wrong and are corrected.
- Practitioner review, decisions 1 to 3. The 164.306 exclusion is confirmed and
  now rests on HHS's own practice rather than our judgement. The nine remaining
  exclusions are confirmed. Decision 3 found a real defect: five standards written
  as a bare `Standard` were missing, including 45 CFR 164.502(a), and the Breach
  Notification Rule was modelled as sections rather than standards. Corrected;
  all three rules now share one shape. Records 191 to 192.
- Practitioner review's Breach paragraph correction merged in PR #35. The two
  incomplete section fallbacks at 164.412 and 164.414 became four complete,
  citable paragraph records. The catalog now contains 194 records: Security 63,
  Privacy 114, and Breach Notification 17.
- Practitioner review approved the subordinate-paragraph boundary: 731
  published child paragraphs beneath 84 HIPAA records remain individually cited,
  non-determinative prompts under their parent. They are neither duplicated into
  parent text nor promoted to assessment results. Record count remains 194.
- Practitioner review approved the Privacy prompt filter. Cited child paragraphs
  are classified as assessment checks, applicability notes, or context; only
  operative assessment checks render checkboxes.
- Practitioner review approved determination-centered Security prompt routing.
  NIST questions route to the implementation specification identified by the
  key activity; genuinely standard-wide questions remain parent guidance.
- Issue #29 now has a representative cleaned Security volume sample for
  164.308(a)(1): 45 raw NIST questions were reduced to 22 determination-useful
  prompts and routed across Risk Analysis (5), Risk Management (6), Sanction
  Policy (4), and Activity Review (7). This is a review sample, not full ingest.
- GitHub issue #20 closed. Three acceptance criteria were superseded when the
  prototype collapsed to the selected Variant A, as recorded in
  `docs/prototypes/v1-ui-prototype-review.md`.
- Prompt volume accepted July 29, 2026, authorising full ingestion on issue #29,
  with the governing assessment/guidance boundary and the curation rule
  delegated to the implementation agent.
- NIST section resolution fixed and guarded. 22/22 Security standards now
  resolve to distinct 800-66r2 sections yielding 443 raw prompts. The guard is
  corpus-wide by design: every standard resolves, no two share a prompt list,
  and per-standard counts are pinned. CI installs a pinned PyMuPDF for that one
  step and fails rather than skips if it is unavailable.
- ADR 0012 accepted: a framework is defined by data, not application code.
  Record shape, rollup rule, status set and presentation mode are declared per
  framework version. Ingestion stays bespoke per source. This constrains the
  Slice 1 data model and is the reason that ticket is not yet written.

## In progress

- GitHub issue #21: practitioner review of the exported 194-record catalog.
  The subordinate-paragraph presentation decision is settled. Review continues
  against stable citation-based record boundaries.
- GitHub issue #29: prompt volume accepted July 29, 2026, so full ingestion is
  authorised. The blocking NIST section-resolution defect is **fixed**. Section
  headings are now parsed once with balanced-paren citation capture, page ranges
  come from consecutive headings, and a NIST citation resolves to a catalog
  standard allowing a trailing `(1)` and/or `(i)`. All 22 Security standards
  resolve to distinct sections, 443 raw prompts, no two standards sharing a
  prompt list. The approved 22-prompt curated set is unchanged; only the raw
  count for 164.308(a)(1) moves, from 45 to 40.
  Ingestion itself has **not** started. Three pieces remain unbuilt: general
  Security routing to replace the eight-entry hand table, general curation under
  the July 29 delegation, and Privacy and Breach role classification across 731
  child paragraphs.

## Blocked

- Slice 4 beyond the catalog is blocked on practitioner review. Building an
  assessment surface on unreviewed assessable units risks reworking every
  determination made against them.

## Open questions

Live but undecided. Not settled enough for `docs/decisions/`, not scoped enough
for an issue. Each names who has to answer it.

- **Evidence mapping in Slice 4 — Johnathan.** Neither assessment mockup has an
  evidence attachment point, because Evidence is Slice 5, after both assessment
  surfaces. Recording is the stated focus, and a determination you cannot attach
  evidence to is half a record. Pulling minimal evidence mapping forward would
  widen Slice 4. Note the mechanic is *map*, not *attach*: one artifact serves
  many records, each mapping carrying its own rationale and lifecycle, per
  AC-007.
- **Launcher in Slice 1 or 1b — Johnathan.** Slice 1 cannot be fully verified
  from a cloud session. Either it lands half-verified until the Windows machine
  catches up, or the launcher splits into its own sub-slice. Blocks writing the
  Slice 1 ticket.

## Known risks

- A guidance extractor verified on one unit can be wrong on every other unit.
  The NIST section-resolution defect passed a full sample review because the
  sample was the only standard the code handled correctly. Extraction work
  should be measured across the whole corpus before any sample is treated as
  representative.

- The HIPAA catalog is ingested but unreviewed, and the first engagement is weeks
  away. The platform runs in parallel with the existing method and is not on the
  critical path of client work.
- The catalog is verified to reproduce the regulation faithfully. It is not
  verified to be a sound assessment instrument; that is a practitioner judgement
  and is the open acceptance criterion on issue #21.
- Three catalog exclusions are judgement calls, not facts, and are recorded with
  reasons in the catalog and the export. 45 CFR 164.306 is the one most worth
  challenging.
- The OCR Audit Protocol predates the current rule text and is not yet ingested.
  It must be reconciled against eCFR when the guidance layer is built, not
  assumed current.
- HHS SRA Tool terms are unassessed. No content from it may be reused until they
  are checked.
- Document templates remain an open input.
- The local `data/` folder contains legacy evidence and exports that must be
  preserved until a separate backup/retention decision is made.
- Launcher, offline operation, packaging, and backup/restore cannot be verified
  from a cloud session. Those belong to Slices 1 and 7 on the Windows machine.
- No additional frameworks in V1. SOC 2 and possibly PCI DSS are considered for
  later with no commitment. Both strain the ADR 0012 model in the same place:
  each wants a client-defined control sitting between the published requirement
  and the determination, which neither CMMC nor HIPAA needs. Nothing is built
  for it; the analysis is recorded in ADR 0012 so it is not rediscovered.

## Next recommended action

Full issue #29 prompt ingestion, in the order the fix unblocked:

1. General Security routing. Replace `SECURITY_SAMPLE_CURATION`, a hand-written
   table covering one standard, with the approved rule: a key activity carrying
   an `Implementation Specification (Required|Addressable)` marker routes to the
   specification it names; the 95 unmarked activities stay on the parent as
   introductory guidance. The general rule must reproduce the approved
   164.308(a)(1) result, or the rule is wrong.
2. General curation under the July 29 delegation.
3. Privacy and Breach role classification across 731 child paragraphs beneath
   84 records, as `assessment_check` / `applicability_note` / `context`.
4. Full ingest and export, records unchanged at 194.

Then Johnathan reviews one fully-prompted standard from each source path. No
assessment UI work before that.

## Deferred decisions and their triggers

Recorded so they resurface on their own rather than when someone remembers.

- **Narrow the V1 boundary — split the required and optional halves of Slices 2, 5
  and 7.** Trigger: **completion of the first real engagement.** This is the single
  biggest lever on how long V1 takes. It is deferred rather than dropped because
  running one engagement is what tells us which half is required; deciding now
  would be guessing. It blocks nothing before Slice 2 — Slice 1's foundation is
  needed at any V1 scope.
