# Issue #143 verification: one-click POA&M draft and the "NOT MET not on a POA&M" count

Date: October 8, 2026. Built on `main` at `a99d6c0` (#140 and #141 merged).
Synthetic data only. #142 was being built in parallel, so this change stays out
of evidence code.

## What changed

- **One-click draft, same endpoint.** The existing `POST
  .../requirements/{record_id}/poam` accepts `{"draft": true}`
  (`api/main.py`). The server then:
  - prefills the title and description from the requirement finding
    (`api/cmmc.py` `poam_draft`);
  - creates the `corrective_actions` row on the requirement finding with status
    **Draft**;
  - records the audit event `cmmc.poam_item_created`, with `status: "Draft"`
    and `prefilled_from_finding: true`.
- **Draft contents.**
  - Title: `<requirement ID> <catalog title>`, for example
    `AC.L2-3.1.2 Transaction & Function Control`.
  - Description: every failed objective, with its citation and text, its
    examine, interview and test notes, any documented interview or
    observation, and its mapped evidence.
- **No duplicates.** A draft request for a requirement that already has an
  open POA&M item (any status other than Closed or Withdrawn) is refused with
  409, and the message names the existing item.
- **NOT MET only.** A draft for a requirement that does not derive Not Met is
  refused with 409. That covers Pending (AC-005) and Met, and is the same check
  the endpoint already had.
- **Never automatic.** Determination saves still only sync the finding. No code
  path creates a POA&M item except this endpoint.
- **Inline editing.** A new `PUT .../requirements/{record_id}/poam/{action_id}`
  edits the title and description of a non-terminal item. It is scoped to the
  project and requirement through `requirement_findings`, and records the audit
  event `cmmc.poam_item_edited`.
- **Unplanned count, derived and not stored.**
  `cmmc.not_met_without_poam` lists requirements that derive Not Met and have
  no open POA&M item. Closed and Withdrawn items do not count as planned. The
  query is filtered by `project_id`. The same figure is returned in two places:
  - `GET /api/projects/{id}/assessment` returns `not_met_without_poam:
    {count, requirement_ids}` for CMMC and `null` for HIPAA. The assessment
    view uses this one.
  - `GET .../cmmc-score` returns it too, for the Overview (ticket 5).
- **UI** (`web/src/views/assessment/PoamSection.tsx`, new):
  - **NOT MET requirement.** The finding panel shows a "Create POA&M draft"
    button. One click creates the draft, which opens inline as an editable
    form with its title focused.
  - **Already planned.** When an open item exists, the button is disabled and
    the reason names that item.
  - **Not NOT MET.** The button is hidden.
  - **32 CFR 170.21 warning.** It is read from this requirement's score
    deduction line (`conditional_poam_allowed`, `poam_reason`, from #141). It
    warns and does not block.
  - **Assessment header count.** The header shows "N NOT MET not on a POA&M".
    Pressing it filters the requirement list to those requirements
    (`RequirementList` `onlyIds`).
  - **POA&M closure.** The `window.prompt` for the closure rationale was
    replaced by an inline required textarea. It sits in the requirement view
    this ticket touches.
  - **Manual form removed.** The old typed "Add POA&M item" form was replaced
    by the one-click draft; see the judgement calls.

## Commands run

| Command | Result |
|---|---|
| `python -m pip install -e ".[dev]"` (venv) | ok |
| `pytest` | 258 passed (253 before: +5 in `test_issue_143_poam_draft.py`) |
| `ruff check .` | All checks passed |
| `mypy catalog api` | Success: no issues found in 66 source files |
| `pnpm install --frozen-lockfile` | ok, lockfile unchanged |
| `pnpm run typecheck` | ok |
| `pnpm run lint` | ok, no warnings |
| `pnpm run test` x3 | 82 passed, 7 files, on each of 3 runs (78 before) |
| `pnpm run build` | ok |

New and changed tests:

- `api/tests/test_issue_143_poam_draft.py` (5 tests):
  - **Prefilled draft.** A one-click draft is prefilled from the finding: both
    failed objectives, the objective note and the mapped evidence, with
    status Draft.
  - **No duplicate.** A second click gets 409, names the existing item, and
    leaves one item.
  - **Audit.** Creation is audited with `prefilled_from_finding`.
  - **Edit.** The draft is editable, an empty title is refused, and the edit
    is audited.
  - **Manual path.** The typed path still starts items as Open.
  - **Never automatic.** Three requirements set to Not Met create zero
    `corrective_actions` rows.
  - **Pending and Met refused.** Pending (AC-005) and Met get 409, and still
    no rows are created.
  - **Count tracks POA&M state.**
    - It starts at 2, and drafting one requirement drops it to 1.
    - The assessment and score APIs agree, and `open_poam_count` matches.
    - Withdrawing the item returns the requirement to the count and allows a
      new draft. A Withdrawn item cannot be edited.
    - A Closed item does not plan a requirement that fails again later.
  - **Project isolation.** A POA&M in project A does not plan the same
    requirement in project B. Project A's item cannot be edited through
    project B's route (404). Each project's duplicate check sees only its own
    items. HIPAA returns `null`.
  - **170.21 data.** A never-POA&M requirement (CA.L2-3.12.4) can still be
    drafted (warn, not block). Its score line carries
    `conditional_poam_allowed: false` and the reason.
- `web/src/PoamDraft.test.tsx` (4 tests, against an in-memory API):
  - **One click.** It sends `{"draft": true}`. The draft opens inline,
    prefilled, with its title focused. The button is then disabled with the
    reason, and a further click sends nothing. Saving sends a PUT to the item
    route.
  - **Warning.** A 5-point requirement shows the 32 CFR 170.21 warning before
    and after the draft. A 1-point requirement shows none.
  - **Header count.** The count reads 2 and filters the list to the two NOT
    MET requirements. Drafting one drops it to 1 and removes that requirement
    from the filtered list. Pressing the count again restores the full list.
  - **Pending and determination changes.** Pending shows no button. Setting
    an objective Not Met shows the button and raises the count, and makes no
    POA&M request.
- Updated:
  - `App.test.tsx`: the manual "Add POA&M item" assertion became the
    disabled-with-reason assertion, and the close test types the rationale
    inline instead of mocking `window.prompt`.
  - `test_issue_m3_assessment_revision_expand.py`: the pinned assessment key
    set gained `not_met_without_poam`.
  - `activeAssessmentFixtures.ts`: score lines now carry `poam_reason`.
- `test_issue_105_*` and `test_issue_108_*` pass unchanged.

## Run against the app

1. Serve the API on an empty data directory. `docs/evidence/issue-140/serve_synthetic_api.py <dir>`
   uses port 8000. Here it was run on port 8143 to avoid the parallel #142
   session, with Vite proxying `/api` to it from port 5243.
2. Run the dev server with `pnpm run dev`.
3. Seed with `API_BASE=http://127.0.0.1:8143 python docs/evidence/issue-143/seed_synthetic_cmmc.py`.
4. Capture with `APP_BASE=http://127.0.0.1:5243/ PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers node docs/evidence/issue-143/capture_screenshots.mjs docs/evidence/issue-143`.

The seed follows the #141 "fieldwork" determinations, with three requirements
left NOT MET:

- AC.L2-3.1.2 at 5 points, with notes and evidence;
- AC.L2-3.1.3 at 1 point;
- SC.L2-3.13.11, partial at 3 points (the named exception).

Measured (Chromium, synthetic):

| Measure | Result |
|---|---|
| Count before (assessment API = score API = header) | 3: AC.L2-3.1.2, AC.L2-3.1.3, SC.L2-3.13.11 |
| 170.21 eligibility from score lines | AC.L2-3.1.2 not allowed (5-point); AC.L2-3.1.3 allowed (1-point); SC.L2-3.13.11 allowed (named exception) |
| Draft title / status | `AC.L2-3.1.2 Transaction & Function Control` / Draft, title focused |
| Draft description | the failed objective [a], its examine and interview notes, `Evidence: synthetic-role-matrix.txt (Synthetic role matrix.)` |
| Forced second click on the disabled button | still one item |
| Count after (all three sources) | 2: AC.L2-3.1.3, SC.L2-3.13.11; filtered list shows exactly those |
| 1-point requirement warning | none |
| Audit rows | one `cmmc.poam_item_created`, `status: Draft`, `prefilled_from_finding: true` |
| Horizontal overflow at 800 px | 0 px |

## Screenshots

| File | Shows |
|---|---|
| `01-not-met-requirement-with-button-and-170-21-warning-1440.png` | NOT MET 5-point requirement: header count 3, the 170.21 warning, "Create POA&M draft" |
| `02-created-draft-inline-1440.png` | The created Draft open inline, prefilled; button disabled with the existing item named |
| `03-header-count-and-filtered-list-1440.png` | Header count 2, pressed; list filtered to AC.L2-3.1.3 and SC.L2-3.13.11 |
| `04-eligible-requirement-no-warning-1440.png` | 1-point requirement: button, no warning |
| `05-draft-and-warning-800.png` | Draft and warning at 800 px |

## Judgement calls

- **Manual form removed.** The typed "Add POA&M item" form in the finding
  panel was replaced by the one-click draft. Keeping it would let a second
  open item be added beside the draft, which defeats "no duplicates". The API
  still accepts a typed title, and the old tests still use it.
- **Duplicate rule applies to drafts only.** One open item per requirement is
  enforced on the draft path only. The typed path keeps its #105 behaviour.
- **Draft counts as planned.** A Draft item takes its requirement out of the
  count. It is an open POA&M record, and `record_states.open_poam_count`
  already counted it.
- **Warning covers every ineligible requirement.** The warning shows for any
  requirement whose score line is not POA&M-eligible: the six never-POA&M
  requirements and any requirement over 1 point, except the 3.13.11 named
  exception. The issue says "never allows" and the brief gives a 5-point
  example; both are covered by `conditional_poam_allowed`.
- **Requirement view only.** The count is shown in the assessment header only.
  The Overview display is ticket 5, which reads `cmmc-score.not_met_without_poam`.
- **Edit window.** A POA&M item can be edited until it is Closed or Withdrawn,
  but the UI shows the editor only for Draft items.

## Not done here

- **Draft to Open.** There is no control yet. The spec moves Draft to Open on
  first assignment, and owners and assignment are a later ticket. The existing
  `PUT /api/projects/{id}/corrective-actions/{action_id}` already allows it.
- **Overview display of the count** is ticket 5.
- **Withdrawn items still block CMMC close.** `api/close.py` `poam_closed`
  counts any item that is not Closed, including Withdrawn. This is pre-existing
  and was left unchanged; it should be confirmed.
