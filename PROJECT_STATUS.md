# Project Status

## Current phase

`BUILD/REVIEW`. GitHub issue #69 is complete and merged through PR #84. GitHub
issue #68 is implemented on `feature/68-remediation-validation` from `main`
commit `97e8e8a`. Focused validation tests, the full API and catalog suites,
Ruff, Mypy, frontend typecheck, ESLint, Vitest, the production build, and a
fresh migration upgrade/downgrade/re-upgrade pass locally. Final Chrome
viewport verification and repository CI remain before completion.

## Current mode

Build and review for Issue #68. The slice adds a project-scoped corrective-action
Ready for Validation state and immutable binary Validated/Failed reassessment.
Only a validated action with mapped evidence or documented interview/observation
may change its linked determination from Not Met to Met. The finding remains
open, and failed validation returns only the action to In Progress.

## Current objective

Complete Chrome verification for Issue #68, finish independent review, update
tests for any findings, commit and push, open a PR, and require passing GitHub
CI before merge. Then implement the usable-pilot critical path in order:
#70, #71, #72, and #73. Issue #66 requires Johnathan's explicit approval of
sanitized report inputs before #71 can release report templates.

## Approved specification

`docs/specification.md`. The Milestone 0 amendment aligning it with the
requirements and implementation plan was approved by Johnathan on August 24,
2026 and merged through PR #51 after both independent review axes and repository
CI passed.

## Active ticket

**GitHub issue #68 - implemented / local review in progress.**

- Migration `0009` adds corrective-action validation state, immutable validation
  events, immutable determination history, composite ownership constraints, and
  SQL triggers that prevent direct unvalidated closure and Not Met-to-Met bypass.
- The API records exactly Validated or Failed outcomes atomically, derives the
  evidence context and assessment revision server-side, verifies actor and full
  project/assessment/record/action ownership, and never closes the finding as a
  side effect.
- The UI supports Ready for Validation, requires notes, shows only the two
  outcomes, and retains finding, action, determination, evidence/interview, and
  validation history after successful closure.
- Local verification passes: focused backend `7 passed`; full API `105 passed`;
  catalog `74 passed`; Ruff; Mypy; frontend typecheck; ESLint; Vitest `46
  passed`; production build; and migration upgrade/downgrade/re-upgrade.
- An independent review found a cross-record SQL-trigger scope weakness and a
  post-validation history visibility gap. Both were remediated and are being
  covered by regression tests before PR creation.

### Recently completed ticket detail

**GitHub issue #74 — complete and merged through PR #82.**

- `migrations/versions/0006_assessment_revision_expand.py` adds two expansion
  tables without rebuilding or weakening `assessments`.
- `assessment_revisions` keeps the existing assessment ID as revision identity,
  records project ownership, positive revision number, and optional predecessor.
  Composite foreign keys bind both the revision and predecessor to one project.
- `project_active_assessments` has one row per assessed project. Its composite
  foreign key binds the active assessment to that project. The initial pointer
  cannot be deleted or re-keyed; a later ticket can update it to a valid
  same-project successor.
- Migration backfill assigns revision 1 with no predecessor and points each
  assessed project at its unchanged current assessment. An assessment insert
  trigger gives newly created assessments the same metadata and pointer while
  leaving the existing API caller and response untouched.
- `api/tests/test_issue_m3_assessment_revision_expand.py` covers clean creation,
  populated upgrade/downgrade/re-upgrade, ID and determination preservation,
  exactly one active pointer, revision-1 metadata, same-client and cross-client
  guessed-ID rejection/no mutation, and direct-SQL cross-project
  pointer/predecessor rejection. The schema represents a successor by the
  reverse predecessor relationship, but the retained assessment uniqueness and
  unchanged API deliberately prevent creating one in this expand phase.
- Verification completed locally: focused `5 passed`; full API `55 passed`;
  catalog `74 passed`; Ruff passed; frontend typecheck and lint passed; Vitest
  `39 passed` including delayed project/assessment response protections; and
  the production frontend build passed. Mypy passes when invoked with the
  repository config after the test helper annotations were corrected.
- Required browser regression evidence passed at 1440x900 and 1280x720 using a
  fresh upgraded database and synthetic data. Next/Previous changed and
  restored the selected record, all required workspace regions remained
  visible, document width matched viewport width, and no console or page errors
  occurred. Evidence and the QA inventory are retained in
  `docs/screenshots/issue-74/`.
- Final independent Standards and Specification reviews both passed with no
  actionable findings after the initial evidence and status-documentation
  findings were remediated.
- Implementation commit `6c19cb5` is pushed to
  `origin/feature/74-assessment-revision-expand`. PR #82 is open against
  `main`, and every GitHub CI job passes.

GitHub issue #62 is complete and merged through PR #64.

GitHub issue #61 is complete and merged through PR #63.

GitHub issue #58 is complete and merged through PR #59.

GitHub issue #53 is complete and merged through PR #57.

GitHub issue #54 is complete and closed through PR #55 after local automated
checks, browser verification, ARM64/x64 source compatibility review, both
independent review axes, and required CI passed.

GitHub issue #50 is complete and closed through PR #51; it was
documentation-only and did not authorize BUILD.

GitHub issue #49 remains an isolated practitioner test. Its result must not
change ADR 0012 or the approved baseline unless Johnathan separately accepts the
test and approves the resulting decision and specification revision.

GitHub issue #44 is complete and merged in PR #46. GitHub issue #32 remains the
Windows launcher and offline-package spike; backup and restore implementation
will be scoped in a separate future ticket after this reconciliation.

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
  That approval unblocked the separately approved Slice 1a work that followed;
  it does not authorize a new BUILD session.
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
- Issue #54's recoverable autosave implementation passed its full local command
  set, browser verification with synthetic data, ARM64/x64 source compatibility
  review, and independent Standards and Specification reviews on August 24,
  2026. It merged to `main` through PR #55 after required CI passed, and the
  issue closed automatically.
- Issue #53's project-scoped immutable local-evidence implementation passed 9
  API tests, 12 React tests, 73 catalog tests with 15 skipped, migration
  upgrade/downgrade and populated-workspace backfill checks, browser isolation
  with synthetic data, ARM64/x64 source compatibility review, and independent
  Standards and Specification reviews on August 24, 2026. It merged to `main`
  through PR #57 after required CI passed and is complete.
- Issue #58's system-owned HIPAA walkthrough merged to `main` through PR #59
  as merge commit `0193c0c`.

## In progress

- **GitHub issue #74**: complete and merged through PR #82. Its assessment
  revision foundation is present on `main` and is the base used by Issue #69.
- **GitHub issue #49**: isolated practitioner test of the question-level working
  record. It does not alter ADR 0012 or authorize production changes.
- **GitHub issue #32**: the Windows package and launch spike. Open, assigned,
  labeled `ready-for-human`, needs Johnathan's machine, and now owns the launcher
  and packaging work that was explicitly excluded from the merged Issue #44
  scope.
- **GitHub issue #21**: practitioner review of the exported 194-record catalog.
  It stays open and `ready-for-human`. Record boundaries are settled and
  citation-stable, and the catalog was read in its working shape through the
  walkthrough. The remaining soundness read is Johnathan's practitioner
  judgement about whether these are the right assessable units rather than
  whether they reproduce the regulation.

No other production slice is in flight. Issue #75 caller migration has not
started and remains dependent on #74 merging. Issues #67 and #69 are the
independent `ready-for-agent` Milestone 3 frontier.

## Ownership

Johnathan remains accountable for product and scope decisions, approvals,
implementation delivery, engineering verification, practitioner acceptance,
framework sign-off, operations, backup/restore acceptance, and benefits
measurement. AI agents provide analysis, drafting, implementation, test
execution, and operational support; repository CI remains the engineering
verification of record. This is the approved joint Johnathan-plus-AI delivery
and operations model, not a claimed segregation of duties.

## Blocked

- Issue #74 has no implementation, review, or CI blocker. PR #82 awaits human
  merge review. Required desktop and 1280x720 browser regression evidence is
  retained in `docs/screenshots/issue-74/`. The frontend itself is unchanged
  and its delayed-response regression suite passes.
- GitHub issue #32 and every claim about the launcher and offline package are
  blocked on Johnathan's Windows machine. A cloud session cannot verify them.
  Backup and restore are approved requirements but are not part of #32; their
  future implementation and ARM64/x64 recovery verification require a separate
  ticket and representative Windows hardware.

## Open questions

Live but undecided. Not settled enough for `docs/decisions/`, not scoped enough
for an issue. Each names who has to answer it.

- **Question-level working record test in Issue #49 — Johnathan.** The test is
  isolated from the approved baseline. If accepted, it requires an explicit
  ADR 0012 disposition and a specification revision before any production work.
- **Editable status on a parent standard — Johnathan.** Raised repeatedly on
  July 30 and answered no, on the grounds that 164.306(d)(2) satisfies a
  standard through its implementation specifications and an independently
  settable parent status would let a standard read Met while one of its own
  specifications reads Not Met. Notes and evidence were added to the parent
  instead, which carry no such contradiction. Recorded here rather than in
  `docs/decisions/` because the question was asked more than once and may not be
  settled in the asker's mind; reopening it is a specification change.
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
- Sanitized document templates remain an input. Until automated enforcement is
  separately approved and built, every template ticket requires a recorded
  manual sanitization gate, verification step, and Johnathan approval.
- The local `data/` folder contains legacy evidence and exports that must be
  preserved until a separate backup/retention decision is made.
- Launcher, offline packaging, and the future fully local backup/restore
  workflow cannot be verified from a cloud session. Those require representative
  ARM64 and x64 Windows machines.
- No additional frameworks in V1. SOC 2 and possibly PCI DSS are considered for
  later with no commitment. Both strain the ADR 0012 model in the same place:
  each wants a client-defined control sitting between the published requirement
  and the determination, which neither CMMC nor HIPAA needs. Nothing is built
  for it; the analysis is recorded in ADR 0012 so it is not rediscovered.

## Next recommended action

Commit and push the Issue #69 Chrome evidence, update draft PR #84, re-run CI,
then mark it ready for human review. Merge only after explicit user approval.

## Branch inventory

Recorded so the next agent does not re-derive it, and because a branch reset in
this repository has already destroyed a day of work once. **Nothing here has
been deleted.** Issues #53, #54, #58, #61, #62, #74, and #67 are merged on
`main` at `c6cb780`. Issue #69 is committed and published on
`feature/69-hipaa-sra` through draft PR #84; keep this worktree and branch until
its PR merges.

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
