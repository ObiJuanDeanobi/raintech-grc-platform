# Issue #140 verification: requirement-centred CMMC assessment view

Date: October 8, 2026. Branch built on #139 (`App.tsx` split). Synthetic data
only.

## What changed

- **CMMC left list** (`web/src/views/assessment/RequirementList.tsx`): the 14
  families expand to their requirements. Each family shows decided objectives
  out of total (for example `AC 8/70`). Each requirement row shows its derived
  status dot, decided/total objectives, an evidence marker, and a POA&M marker.
  The POA&M marker reads `POA&M` when items are open and `No POA&M` when the
  requirement is Not Met with no open item. Objectives are no longer rows in the
  list.
- **Requirement view** (`web/src/views/assessment/RequirementWorkspace.tsx`):
  - The requirement text, with practitioner guidance in a collapsed section.
  - One row per objective with one-click Met / Not Met / Pending. CMMC has no
    N/A. Each row carries an evidence marker and expandable Examine / Interview
    / Test notes, plus the documented interview/observation field that the
    existing Met rule accepts.
  - Below the objectives: the implementation statement, and linked evidence for
    the focused objective (the existing evidence panel, reused).
  - Scoring/POA&M follows, then the full SSP panel, folded away.
  - The score is a single line in the toolbar.
- **Interview view**: the same rows, one objective at a time, with previous and
  next objective buttons. Toggle at the top right.
- **Keyboard**: Up/Down move between objectives; M / N / P set Met / Not Met /
  Pending; J / K and ] / [ move between requirements. The keys are shown above
  the objective table. Keys are ignored while typing in inputs, textareas and
  selects, while another view is open, and while the new-project dialog is open.
- **Save failure** (`web/src/components/routineSave.ts`,
  `RoutineSaveStatus.tsx`):
  - The autosave hook now keeps the API's error message and the last saved
    value.
  - A refused objective shows `Save failed · <API reason>. Saved status is
    still <last saved>` and a Retry button. The selected button stays on the
    last saved status; the attempted one is outlined in dashed red.
  - The HIPAA determination panel gets the same reason, and its pill shows the
    last saved status.
- **Landing**: a CMMC assessment opens on the first requirement with an
  objective that is not Met or Not Met.
- **API** (`api/main.py`): `GET /api/projects/{id}/assessment` gains a
  read-only `record_states` map: status, evidence count and open POA&M count per
  record. Derived statuses use the same rollup as the record detail; the rollup
  was factored into `_rollup_status`, with no behaviour change. No migration and
  no new endpoint.

## Judgement calls

- **Per-objective notes** use the existing `record_notes` row as labelled plain
  text (`Examine: …` / `Interview: …` / `Test: …`; see
  `web/src/lib/objectiveNotes.ts`). There is no migration. SSP drafting already
  quotes objective notes, so the labelled text reads naturally there. Text
  written before #140 stays as unlabelled "Earlier notes". One limit: a line
  typed as `Test: …` inside another field is read back as a test note.
- **Implementation statement.** Before an SSP exists, the statement is the
  requirement's record note. SSP generation already uses that note as the first
  line of the drafted implementation. It autosaves on blur and creates no SSP
  version. Once an SSP draft exists, every SSP edit appends a version, so the
  statement is written there only by **Save to SSP draft**: one version per
  click, never per keystroke. An approved SSP shows the statement read-only.
- **"Decided"** means Met or Not Met, matching the API's "resolved" count.
  Pending leaves an objective open, for the family counts and for landing.
- **`record_states`** was added to the existing assessment response instead of
  making 110 detail requests. The revision-contract test that pins the
  response's key set now lists it.
- **Narrow widths.** The page keeps its 1120 px minimum width for every view
  except the CMMC assessment, which reflows below 1000 px (scoped with `:has`).
  Measured horizontal overflow at 800 px: 0.

## Commands run

| Command | Result |
|---|---|
| `python -m pip install -e ".[dev]"` (venv) | ok |
| `pytest` | 243 passed (240 before #140, plus 3 new) |
| `ruff check .` | All checks passed |
| `mypy catalog api` | Success: no issues found in 63 source files |
| `pnpm install --frozen-lockfile` | ok (lockfile unchanged, no new packages) |
| `pnpm run typecheck` | ok |
| `pnpm run lint` | ok |
| `pnpm run test` x3 | 76 passed, 6 files, on each of 3 runs (68 before #140, plus 8 new) |
| `pnpm run build` | ok (dist built) |

New tests:

- `api/tests/test_issue_140_record_states.py`
  - Markers follow determinations, evidence and POA&M, and agree with the record
    detail.
  - Same-client, cross-client and HIPAA isolation.
  - The statement and labelled objective notes reach the next SSP draft, which
    holds a single version.
- `web/src/RequirementWorkspace.test.tsx`
  - Lands on the actionable requirement, with family counts, markers and CMMC
    statuses only.
  - Keyboard-only determination, with the score updating without a reload and
    J/K/[/] navigation; keys are not hijacked while typing.
  - A refused Met shows the API reason and the last saved status, and Retry
    succeeds.
  - Per-objective notes autosave and load back.
  - Statement to SSP, both before generation and as one explicit version after.
  - Interview view.
  - Notes format round-trip.
- `web/src/App.test.tsx`
  - A refused HIPAA determination shows its reason and the last saved status.
  - Two CMMC tests that encoded the objective-per-page layout were rewritten to
    the requirement view. No isolation, autosave-ordering or security test was
    changed.

## Run against the app

1. Start the API on a throwaway directory:
   `python docs/evidence/issue-140/serve_synthetic_api.py <dir>`.
2. Start the frontend with `pnpm run dev`.
3. Seed with `python docs/evidence/issue-140/seed_synthetic_cmmc.py`.
4. Capture with
   `PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers node docs/evidence/issue-140/capture_screenshots.mjs docs/evidence/issue-140`.
   The script imports the globally installed Playwright, from
   `/opt/node22/lib/node_modules`.

Measurements (Chromium, synthetic project):

| Measure | Result |
|---|---|
| Page transitions to decide one requirement (AC.L2-3.1.2, including a refused Met and its correction) | **0** (the requirement heading never changed) |
| y of the first objective row at 1440x900 | **293 px** (previously about 850 px, per `current-app.md` friction point 7) |
| AC.L2-3.1.1, 6 objectives, at 1440x900 | all 6 visible; last row ends at 550 px |
| Opening requirement | AC.L2-3.1.2 (AC.L2-3.1.1 fully decided); after deciding it, AC.L2-3.1.3 |
| Refused Met reason shown | "Met requires mapped evidence or a documented interview/observation. Saved status is still Blank" |
| Score after a Not Met, without reload | 105 of 110 · provisional |
| Family counts sum | 70+9+29+44+25+14+10+15+4+16+9+14+41+20 = 320 objectives |
| Horizontal overflow at 800 px | 0 px |
| First objective row y at 800 px wide | 402 px |

## Screenshots

| File | Shows |
|---|---|
| `01-requirement-view-1440.png` | Landing on the actionable requirement, all objectives with one-click buttons, statement and linked evidence |
| `02-failed-save-1440.png` | A refused Met with the API reason, the last saved status and Retry |
| `03-requirement-view-six-objectives-1440.png` | All six AC.L2-3.1.1 objectives on one screen, evidence marker |
| `04-interview-view-1440.png` | Interview view: one objective, its notes and observation field |
| `05-family-list-1440.png` | Family list with per-family decided counts |
| `06-requirement-view-800.png` | Requirement view at 800 px |
| `07-failed-save-800.png` | Keyboard `M` refused at 800 px, with the reason |
| `08-interview-view-800.png` | Interview view at 800 px |
| `09-family-list-800.png` | All 14 families with counts at 800 px |

## Not done here

- Evidence-pending Met and verified/projected scores (#141). The existing API
  rule still refuses Met without evidence or an observation, and the UI shows
  its message.
- Evidence library view (#142), one-click POA&M (#143), HIPAA layout (#149).
- No Windows or Surface run.
- CI has not run; this branch is local only.
