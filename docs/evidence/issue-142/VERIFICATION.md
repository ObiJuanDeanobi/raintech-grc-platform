# Issue #142 verification: evidence library, multi-objective linking, staleness

Date: October 8, 2026. Built on `main` at `a99d6c0` (#139, #140, #141 merged).
Synthetic data only.

## What changed

- **Staleness in the one verification predicate** (`api/verification.py`).
  `CURRENT_MAPPING` now also requires the artifact's review date to be empty or
  not yet passed (`review_date >= :today`). `met_bases()` takes an optional
  `today`, defaulting to `evidence_lifecycle.today()`. Nothing else decides
  verification, so the verified score (`api/cmmc.py`), record states, record
  detail and close readiness (`api/close.py`) all follow it unchanged.
  - Determinations and `determination_history` are never written by staleness.
    It is computed on read; there is no scheduler.
  - A documented interview/observation still verifies on its own, as in #141.
- **Review status** (`api/evidence_lifecycle.py`). `review_status()` returns
  `current`, `due_soon` or `stale`:
  - No review date: current.
  - Review date passed: stale. This is the same boundary as the #119 `overdue`
    flag.
  - Within the lead time, including the review date itself: due soon. Due soon
    still verifies.
  - `today()` is the single clock. Tests replace it.
- **Project lead time**, migration `0021` (`projects.evidence_review_lead_days`,
  `INTEGER NOT NULL DEFAULT 30`). The default of 30 comes from the
  specification's Recurring Reviews section.
  - Set with `PUT /api/projects/{id}/evidence-settings` (0 to 365, audited).
  - Downgrade refuses while any project has a non-default value, so it never
    discards one silently.
  - This is the only schema change. Existing artifacts without a review date are
    current, and existing mappings are unchanged.
- **Library and linking API** (`api/evidence_library.py`, new; routes in
  `api/main.py`):
  - `GET /api/projects/{id}/evidence-library` lists every live artifact with
    `review_status`, `days_until_review`, `used_by` (the active assessment's
    objective mappings with citation, requirement and rationale) and
    `other_use_count` (Profile and risk mappings).
  - `POST …/assessments/{a}/evidence-mappings/bulk` maps one artifact to several
    objectives in one transaction. It is all or nothing:
    - an objective that already carries the artifact returns 409;
    - a non-objective record returns 422;
    - a binned artifact returns 409;
    - a foreign project's artifact returns 404.
    Each mapping is its own row with its own copy of the rationale (AC-007), and
    each is audited.
  - `PUT …/evidence-mappings/{m}/rationale` edits one mapping's rationale. The
    previous rationale is kept in the audit event.
  - `POST /api/projects/{id}/evidence/{artifact}/versions` accepts two optional
    form fields:
    - `review_date` sets the next review date in the same act.
    - `move_mappings=true` pins the active assessment's mappings to the new
      version. Each move is audited as `evidence.mapping_version_moved`, the
      same event "Use latest version" writes.
    Without either field, replacement behaves exactly as in #119.
  - `record_states[*].evidence_review` gives the worst review status of a
    record's mapped evidence (`due_soon`, `stale` or null). A requirement takes
    the worst of its objectives. Record-detail evidence rows and
    `GET /evidence` gain `review_status` and `days_until_review`.
- **UI**:
  - **Evidence** is a new workspace view in the top navigation
    (`web/src/views/evidence/EvidenceLibraryView.tsx`). It shows a table of
    artifacts with name, short hash, version, an editable review date, a status
    pill, and "Used by N".
    - "Used by N" expands to the mapped objectives. Clicking one opens it,
      focused, in the requirement view.
    - Status filters, the lead-time setting, upload, Renew/Replace and the
      recycle bin are also on this view.
    - Renew/Replace takes a new version, the next review date, and "Move the N
      linked objectives to the new version" (ticked by default).
    - Move to bin is disabled while the artifact is in use.
  - **Link evidence** on the requirement view
    (`web/src/views/assessment/LinkEvidencePicker.tsx`) works in one act:
    - pick a library file or upload one;
    - tick objectives (the focused one starts ticked; already-linked ones are
      disabled);
    - write one rationale.
    It replaces the per-record choose/rationale/Map form on CMMC requirement
    views. HIPAA's working-record panel keeps its form.
  - **Mapped evidence** (`EvidencePanel`):
    - Each rationale has an Edit control.
    - Stale evidence shows "Review overdue since …" and "Stale: no longer
      verifies a Met"; due-soon evidence shows "Review due in N days".
    - Labels show the file name and a 12-character hash. The full SHA-256 is
      only in the tooltip.
    - The collapsed `<details>` library and recycle bin that every record used
      to carry moved to the Evidence view.
  - **Objective rows** show "Evidence stale" or "Evidence due soon" next to
    "Evidence pending".
  - **Styles** are in `web/src/views/evidence/evidence.css` so the shared
    `styles.css` is untouched.

## Tests

`api/tests/test_issue_142_evidence_staleness.py` (10 tests). "Today" is injected
by monkeypatching `api.evidence_lifecycle.today`.

- `test_review_status_boundaries`: current, due soon at +30 and on the review
  date itself, stale at −1, a lead time of 0, and the same boundary as #119
  `overdue`.
- `test_met_bases_drop_evidence_once_review_date_passes`: a unit test of the
  `CURRENT_MAPPING` predicate with explicit dates: evidence on 10-31 and 11-01,
  `None` on 11-02, and evidence again once the date is cleared.
- `test_stale_evidence_returns_verified_met_to_pending_and_lowers_verified_score`
  (AC-024):
  - One artifact is mapped to all six AC.L2-3.1.1 objectives, and every other
    requirement is verified by observation.
  - While the evidence is current, verified and projected are both 110.
  - After the review date passes, verified is 105 and projected stays 110.
    `evidence_pending == ["AC.L2-3.1.1"]`.
  - Record states and record detail say evidence pending and stale, and the
    status is still Met.
  - The `determinations` rows (including `updated_at`) and
    `determination_history` are byte-identical before and after.
  - Close readiness lists exactly the six objectives as `met_evidence_pending`.
- `test_observation_still_verifies_when_evidence_goes_stale`.
- `test_renewing_with_a_current_version_restores_verified`:
  - Replace with `review_date` and `move_mappings` gives version 2 and moves all
    mappings.
  - Verification is restored and the verified score rises by 5.
  - The audit trail has `evidence.replaced`, `evidence.review_date_set` and one
    `evidence.mapping_version_moved` per mapping.
- `test_replace_without_renewal_fields_is_unchanged`: under #119 rules the
  mapping stays pinned to v1, the review date is kept, the stale Met stays
  pending, and a bad date returns 422.
- `test_due_soon_uses_project_lead_time_and_does_not_unverify`: due soon at 20
  days with a 30-day lead, still verified, and current after the lead time
  changes to 14. A negative lead time returns 422.
- `test_bulk_mapping_is_atomic_and_each_mapping_keeps_its_rationale` (AC-007):
  - The 409 for a duplicate writes nothing, and a requirement target returns 422.
  - `used_by` lists exactly the mapped objectives.
  - Editing one rationale leaves the others unchanged, and a blank rationale
    returns 422.
  - Unmapping one mapping leaves the others.
- `test_binned_evidence_cannot_be_bulk_mapped_and_projects_are_isolated`.
- `test_lead_time_migration_cycle_and_downgrade_guard`: upgrade to head,
  downgrade to 0020, upgrade again, and the guard refuses once a project has 45
  days.

Mutation check: with the staleness clause removed from `CURRENT_MAPPING`, four
of these tests fail. They are the predicate unit test, the AC-024 score test,
the renewal test and the plain-replace test.

Existing tests updated for additive response fields only:

- `test_issue_140_record_states`: `evidence_review: None`.
- `test_workspace_api` (0001 backfill): `review_status`, `days_until_review`.
- `App.test.tsx`: the recycle bin is reached through the Evidence view.

The #106 and #119 suites pass unchanged, so hash verification, versioning and
the recycle bin behave as before.

Frontend (`web/src/EvidenceLibrary.test.tsx`, 6 tests):

- The Evidence view lists current, due-soon and stale artifacts.
  - Status text is shown.
  - The label shows the short hash, and the full hash appears only as the
    tooltip.
  - Move to bin is disabled while an artifact is in use.
  - "Used by 2" expands, shows "pinned to v1", and clicking an objective opens it.
  - The status filter works and the recycle bin is shown.
- Renewing a stale artifact posts FormData with the file, `review_date` and
  `move_mappings=true`, and the "stays stale" warning clears once the date is in
  the future.
- The review date saves on blur, and the lead time saves.
- `artifactLabel` gives name · version · 12-character hash.
- Link evidence (AC-007):
  - The option label carries the short hash only.
  - The focused objective starts ticked; ticking a second one sends one bulk
    POST with both IDs and one rationale, and no single-record map calls.
  - Editing one mapping's rationale leaves the other's.
  - On reopen, already-linked objectives are disabled.
- A stale-evidence Met row shows "Evidence stale" and "Evidence pending" with
  Met still pressed. The panel shows "Stale: no longer verifies a Met" and the
  short hash.

## Commands run (all passed)

```
python -m pip install -e ".[dev]"          # in .venv
pytest                                     # 263 passed
ruff check .                               # All checks passed!
mypy catalog api                           # Success: no issues found in 67 source files
python -m unittest discover -s tests       # Ran 97 tests, OK (skipped=15)
pnpm install --frozen-lockfile             # Already up to date
pnpm run typecheck                         # tsc --noEmit, clean
pnpm run lint                              # eslint web, clean
pnpm run test   (x3)                       # 7 files, 84 tests passed, each run
pnpm run build                             # built (index 343.67 kB JS, 53.42 kB CSS)
```

## App run on synthetic data

The API was served with `python docs/evidence/issue-140/serve_synthetic_api.py <empty-dir>`
and the frontend with `pnpm run dev`. The data was seeded with
`python docs/evidence/issue-142/seed_synthetic_evidence.py` and captured with
`PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers node docs/evidence/issue-142/capture_screenshots.mjs docs/evidence/issue-142`
(Chromium from `/opt/pw-browsers`).

Seed output (API, before any UI action):

- While the policy was current: verified `110 = 110`, projected `110 = 110`.
- After the policy's review date was set to 2026-09-30, eight days ago:
  - Verified was `110 − 5 = 105` and projected `110 = 110`.
  - AC.L2-3.1.1 was `status: Met`, `verification: evidence_pending`,
    `evidence_review: stale`.
  - AC.L2-3.1.2[a] was `verified` and `due_soon`.

Captured from the running app:

| Screenshot | Shows |
| --- | --- |
| `01-evidence-view-current-due-soon-stale-1440.png` | Evidence view with two current artifacts, one due soon ("Review due in 12 days") and one stale ("Review overdue since 2026-09-30"). Short hashes, "Used by N", one not linked, recycle bin with one artifact. |
| `02-used-by-expanded-1440.png` | The stale policy's "Used by 3" expanded to AC.L2-3.1.1[a]–[c] with their rationales. |
| `03-requirement-view-met-returned-to-evidence-pending-1440.png` | Opened from the library on 3.1.1[b]. Objectives [a]–[c] are still Met (pressed) with "Evidence pending" and "Evidence stale"; [d]–[f] are verified. The toolbar shows verified 105, projected 110. The panel shows "Stale: no longer verifies a Met". |
| `04-multi-objective-link-picker-1440.png` | The Link evidence picker: one library file, objectives [b], [d] and [e] ticked, one rationale, and the button "Link to 3 objectives". |
| `05-objective-evidence-due-soon-1440.png` | AC.L2-3.1.2[a] row with "Evidence due soon", still verified, and "Review due in 12 days" in the panel. |
| `06-renew-stale-artifact-1440.png` | The Renew form on the stale policy: new file, next review date 2027-10-08, and "Move the 3 linked objectives to the new version" ticked. |
| `07-requirement-view-verified-after-renewal-1440.png` | After renewal: AC.L2-3.1.1 has no evidence-pending rows, verified is 110, Conditional is Eligible, and the mapping shows Version 2. |
| `08-evidence-view-800.png` | The Evidence view at 800 px wide, after renewal, with "Used by" expanded. Horizontal overflow is 0 px. |

Measured in the capture run:

- `score_line_stale` showed verified 105 and projected 110.
- `score_line_renewed` showed verified 110, Conditional Eligible.
- `pending_rows_after_renewal` was 0.
- `horizontal_overflow_800` was 0.

## Not done / judgement calls

- **Staleness is per artifact** (one review date), not per mapping. The
  specification edge case "evidence supports several requirements but becomes
  stale for only one use" is not covered. The ticket scoped the review date
  as the existing artifact field.
- Because the review date is on the artifact, moving it forward also
  re-verifies mappings still pinned to an older version. Renew moves the
  mappings to the new version by default, so a verified Met rests on the renewed
  file. An unticked move leaves the pin, as #119 intends.
- The lead time is project-level, as the ticket says. The specification's
  Recurring Reviews section allows it per item; per-artifact lead times are not
  built.
- `used_by` lists the active assessment's objective mappings only. Profile and
  risk mappings are counted in `other_use_count` and block binning, but they
  are not linked.
- Bulk mapping across requirements is deferred, per the ticket's accepted debt.
  The API accepts any objectives of the assessment; the UI offers one
  requirement's objectives.
- Due-soon and stale evidence do not yet feed an action queue or Overview count.
  That belongs to the Overview and queue tickets.
- Migration number: this is `0021`. #143 is being built in parallel. If it also
  adds a migration, whichever merges second renumbers to `0022` and updates its
  downgrade test.
