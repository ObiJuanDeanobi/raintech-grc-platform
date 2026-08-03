# Project Status

## Current phase

Slice 4a complete. Slice 1a is merged to `main` in PR #46 after independent
review and green GitHub CI. GitHub issue #49 is now an isolated practitioner
test of question-level HIPAA working records; it is not approved architecture.

## Current mode

BUILD. Issue #49 has an approved local test scope and is awaiting practitioner
feedback before any architecture or specification change.

## Current objective

Validate whether each assessable HIPAA question should be the unit of working
record while guidance-only prompts remain non-determinative. Launcher and
packaging remain separately tracked in Issue #32.

## Approved specification

`docs/specification.md`. Approved July 23, 2026; post-prototype revision, catalog
count correction and bare-standard correction approved July 27, 2026; Breach
paragraph correction approved July 28, 2026. No unapproved changes outstanding.

## Active ticket

GitHub issue #49 is active on `codex/question-working-record-test` as a local
practitioner test. It deliberately challenges ADR 0012 without revising it.
GitHub issue #44 remains complete and merged in PR #46. Launcher, offline
packaging, and backup/restore remain Issue #32.

GitHub issue #29 is closed. The prompt layer is ingested, practitioner-reviewed
on a clickable walkthrough, and merged.

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
- General Security routing built and committed at
  `docs/catalogs/security-prompt-routing.md`. Replaces the eight-entry hand
  table with the marker rule; all 22 standards route, every implementation
  specification receives prompts, 444 routed with no warnings.
- Minimal evidence mapping pulled forward into Slice 4, confirmed by Johnathan
  on review of the clickable walkthrough, July 30, 2026. This closes the
  standing open question. The mechanic is *map*, not upload: one artifact
  supports many records, each mapping keeping its own rationale and lifecycle,
  per AC-007. The specification already makes this non-optional — a final Met
  determination requires mapped evidence or a documented interview/observation
  record — so a Slice 4 assessment surface without it cannot produce a valid
  Met. Slice 5 still owns the full evidence lifecycle: versioning, replace,
  detach, recycle bin, archive, deduplication, staleness, manifest export, and
  evidence requests.
- Three further recording fields are required by the specification and were
  missing from the walkthrough alongside evidence: N/A rationale, which HIPAA
  requires on every N/A; the addressable disposition recording whether the
  standard measure, an equivalent alternative, or a documented
  non-implementation decision is used, which applies to 22 of the 41 Security
  implementation specifications and has no CMMC equivalent; and per-record
  notes for the implementation discussion.
- Unmarked-key-activity routing decided (issue #29): route by the marker rule,
  render parent guidance in view while a child determination is worked, and
  promote individual questions to a child by exception on rendered output. The
  implementation specification is treated as the CMMC-style objective that
  carries the determination; the standard is its rollup. Chosen to keep the
  HIPAA walkthrough as close as possible to how a CMMC gap analysis is run,
  without authoring an uncitable question-to-record mapping.
- ADR 0012 accepted: a framework is defined by data, not application code.
  Record shape, rollup rule, status set and presentation mode are declared per
  framework version. Ingestion stays bespoke per source. This constrains the
  Slice 1a data model, which is now written as issue #44.
- Issue #29 closed. The prompt layer is ingested and practitioner-reviewed on a
  clickable walkthrough built over the real catalog: 1163 prompts beneath 141 of
  the 194 records. Reviewing the working shape rather than a Markdown table is
  what made the review possible, and every design change below came from
  clicking it rather than from reasoning about it.
- Clickable walkthrough built at `catalog/render_walkthrough.py`. It reads the
  same two pinned files the Markdown export reads, so it cannot drift from the
  catalog. **It is a review instrument and is not promoted into production**;
  the Slice 4 surface is reimplemented against the real architecture. Regenerate
  with `python catalog/render_walkthrough.py --out <path.html>` and open the
  file directly. It carries: the 149-record work list with Next/Previous,
  per-question answers, per-record determination, notes, evidence mapping,
  addressable disposition, N/A rationale, standard-level notes and evidence, and
  in-place question moving with JSON export.
- Bullet-fragment key-activity names fixed. A wrapped 800-66r2 cell continues on
  a row beginning with its bullet, and that spill was read as a new activity
  name, producing six phantom activities that competed for routing. 443 raw
  prompts either way, but ten records' prompts moved onto the child they
  belonged to.
- Routing exceptions mechanism added, with the first two decisions recorded:
  `Implement the Information System Activity Review and Audit Process` promoted
  to 164.308(a)(1)(ii)(D), and `Draft, Maintain, and Update Required
  Documentation` rejected for promotion to Updates because it spans all three
  children. Rejections are kept so the same proposal is not re-litigated.
- Automatic title matching for untagged key activities measured and **rejected**:
  2 of 3 candidates correct at the strict threshold, roughly a quarter at a
  looser one, and it fails silently. Kept as a candidate generator only.
- Evidence, notes, and the recording fields settled on the walkthrough: evidence
  is mapped rather than uploaded, the Met gate honours either mapped evidence or
  a documented interview/observation record, N/A requires rationale, addressable
  specifications require a disposition, every question has its own answer field,
  and a parent standard records notes and evidence but never an editable status.
- Issue #44 implemented as the first production vertical slice: Alembic-managed
  SQLite schema; read-only framework seeding; clients, projects, assessments,
  determinations, notes, prompt answers and placements, evidence mappings, and
  audit attribution; plus the React determination-centered workspace.
- The Slice 1a service enforces the approved rollup, N/A, addressable, and Met
  evidence/interview rules at the API boundary. One artifact maps to multiple
  records with independent rationales, and prompt placements persist separately
  from the rebuilt prompt layer.
- Local verification passed: 5 API/service tests, 3 component/integration tests,
  73 existing catalog tests, all 17 required NIST/PDF tests, Python lint/types,
  frontend typecheck/lint/build, byte-identical regeneration of the catalog,
  prompt layer, and export, and browser QA at 1440x900 and 1280x720 with no
  console warnings or errors. Screenshots are in `docs/screenshots/issue-44/`.
- Independent review closed the production-CI gap, made parent guidance
  questions visible in their collapsed context panel, preserved context-routed
  questions on a dedicated surface, prevented removal of the final evidence
  supporting a Met determination, exposed the approved rejection ledger, and
  made statuses and rollups consume the framework declarations.
- The production Overview and post-setup client/project creator are implemented
  and browser-verified. The live browser pass found no console errors.
- Issue #44's 22-criterion Slice 1a implementation merged to `main` in PR #46
  as squash commit `1961cdb` after all GitHub CI jobs passed.

## In progress

- **GitHub issue #49**: local practitioner test of question-level working
  records. Assessable questions own status, notes, evidence, and optional support
  rationale; CFR records and standards roll up those results. Johnathan's test
  feedback determines whether ADR 0012 and the specification should change.
- **GitHub issue #32**: the Windows package and launch spike. Open, assigned,
  needs Johnathan's machine, and now owns the launcher and packaging work that
  was explicitly excluded from the merged Issue #44 scope.
- **GitHub issue #21**: practitioner review of the exported 194-record catalog.
  Record boundaries are settled and citation-stable, and the catalog was read in
  its working shape through the walkthrough. Stays open for the remaining
  soundness read, which is a judgement about whether these are the right
  assessable units rather than whether they reproduce the regulation.

No second approved production slice is in flight. Issue #49 remains an isolated
test branch until practitioner review is complete.

## Blocked

- GitHub issue #32, and every claim about offline operation, packaging,
  launcher, and backup/restore, is blocked on the Windows machine. A cloud
  session cannot verify any of it. #32 blocks only the launcher and packaging
  part of the foundation, not #44's workspace.

## Open questions

Live but undecided. Not settled enough for `docs/decisions/`, not scoped enough
for an issue. Each names who has to answer it.

- **Security prompt routing sweep — Johnathan.** 143 questions sit on parent
  standards across 11 standards with five or more each. 800-66r2 tags a key
  activity with its implementation specification inconsistently, so an untagged
  activity lands on the standard whether or not it belongs there. Hand-checking
  45 CFR 164.308(a)(1) found only 2 of 18 survive: ten belong to that
  standard's own children, six belong to entirely different standards. The test
  is the practitioner's: *to mark a question Met, name the rule it would be Met
  against; name it and the question belongs on that rule's record, fail to and
  it is context.* Automating it was measured and rejected -- title matching
  agreed on 2 of 3 candidates at best and fails silently. The walkthrough
  carries the mechanism (`move…` on every question, with export), so this is a
  pass through the tool, not a decision to reason out. Blocks nothing; the
  routing is usable now and improves with each pass.
- **Question-level working record model — Johnathan.** Issue #49 tests whether
  every assessable question, including standard-level questions, should own its
  status, notes, and evidence while the CFR record or standard derives its
  result. Guidance-only prompts remain non-determinative. Acceptance requires an
  ADR 0012 and specification revision before merge; rejection leaves the
  approved record-level model unchanged.
- **Client-defined control layer — Johnathan.** Surfaced from ADR 0012 during
  the same discussion. SOC 2 and PCI DSS both want a client control sitting
  between the published requirement and the determination, and HIPAA hints at it
  through the addressable "equivalent alternative measure". Nothing is built and
  nothing should be; ADR 0012 preserved the architecture that would allow it.
  Live only because Johnathan showed interest in the shape of it.


## Known risks

- A guidance extractor verified on one unit can be wrong on every other unit.
  The NIST section-resolution defect passed a full sample review because the
  sample was the only standard the code handled correctly. Extraction work
  should be measured across the whole corpus before any sample is treated as
  representative.

- The first engagement is weeks away. The platform runs in parallel with the
  existing method and is not on the critical path of client work, which is what
  makes the remaining schedule risk tolerable.
- Slice 1a has not yet run during a real engagement. Local restart persistence,
  rule enforcement, and representative UI flows are verified; operational
  feedback begins with the first sanitized assessment.
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

Johnathan tests issue #49 locally and accepts, rejects, or refines the
question-level interaction. If accepted, revise ADR 0012 and the specification
for explicit approval before merging. Issue #32 remains the separate Windows
launcher and packaging track.

Independently and at any time, Johnathan can make a pass over the Security
routing in the walkthrough using the `move…` control and send the exported JSON;
it is folded into `ROUTING_EXCEPTIONS` as recorded decisions. Partial passes are
useful — the worst three standards are 164.308(a)(5) with 24 questions on the
parent, 164.312(a)(1) with 21, and 164.308(a)(1) with 18.

## Branch inventory

Recorded so the next agent does not re-derive it, and because a branch reset in
this repository has already destroyed a day of work once. **Nothing here has
been deleted.** `main` is the only branch carrying current work.

Provably merged — every commit has an equivalent already on `main`, verified
with `git cherry origin/main origin/<branch>`. Safe to delete:

- `agent/record-hipaa-child-paragraph-decision`
- `agent/record-nist-section-defect`
- `agent/record-privacy-prompt-filter`
- `agent/record-security-prompt-routing`
- `agent/resume-hipaa-practitioner-review`

Not provably merged. `git cherry` reports commits with no equivalent on `main`,
which is expected after a squash merge rewrote them but is **not proof** either
way. Check with `git log origin/main..origin/<branch>` and a content diff before
touching any of these:

- `agent/hipaa-breach-paragraph-records` — 2 commits. Its work reached `main`
  through PR #35.
- `claude/raintech-spec-approval-rhze0u` — 2 commits. PR #41 recorded it as
  holding nothing that is not on `main`, and older than it.
- `codex/v1-ui-prototype` — 12 commits, ~2800 lines. The V1 UI prototype, whose
  outcome was deliberately collapsed into `legacy/prototypes`. Largest and least
  certain; leave it alone unless Johnathan says otherwise.

## Deferred decisions and their triggers

Recorded so they resurface on their own rather than when someone remembers.

- **Narrow the V1 boundary — split the required and optional halves of Slices 2, 5
  and 7.** Trigger: **completion of the first real engagement.** This is the single
  biggest lever on how long V1 takes. It is deferred rather than dropped because
  running one engagement is what tells us which half is required; deciding now
  would be guessing. It blocks nothing before Slice 2 — Slice 1's foundation is
  needed at any V1 scope.
