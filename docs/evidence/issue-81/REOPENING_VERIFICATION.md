# Issue #81 substantive reopening verification

September 30 to October 2, 2026. Synthetic data only. Branch `claude/issue-81-substantive-reopening`, merged with `main` at `9cc66eb`.

## What was built

- Migration `0015` adds append-only `assessment_reopenings` and `revalidation_items`. The `current_issuances` view and one-current-issue trigger now also treat an issue as superseded once its reopening's successor assessment is issued. A reconciliation rule moves from per-project to per-assessment, with a trigger that keeps one corrective action tied to one record in every revision. See ADR 0018.
- `POST /api/projects/{project}/packages/{package}/reopen` requires `classification: "substantive"`, at least one known affected record, and a rationale. It creates the successor assessment, copies determinations, notes, prompt answers, placements, reconciliations, and assessment-record evidence mappings, and creates one `Needs Revalidation` item per affected record. Project findings, corrective actions, risks, and evidence files are not copied.
- `POST .../records/{record}/revalidate` resolves an item once, with a note and actor.
- Close readiness blocks on unresolved revalidation items and reads project-level risks. Generation, review, backup, and issue then run unchanged.
- Earlier-revision issued packages stay listed, downloadable, and read-only.
- UI: reopen form on the current issued package (explicit classification, searchable affected-record selection, reason), a Needs Revalidation panel with per-record revalidation, and an "Earlier revision package" card with the supersession link.

## Automated evidence

`api/tests/test_issue_m3_substantive_reopening.py` has 9 tests covering:
- Full cycle. Reopen, blocked close and generation, revalidate, regenerate, review, backup, issue. The prior package is superseded, still downloadable, and exactly one current issue survives restart.
- Prior snapshot, package, component, sign-off, backup, and issue rows unchanged. Project findings, corrective actions, risks, and evidence versions keep their IDs and row counts.
- Successor reconciliations have new IDs but reference the same finding and corrective action.
- A prior sign-off cannot authorize the new package; a backup before sign-off is refused.
- Classification, rationale, and unknown-record validation with no writes.
- Retry and stale or cross-project and guessed-ID reopen and revalidate rejection with no new rows.
- Direct-SQL probes: reopening and revalidation immutability, forged revalidation items, double resolution, a second issue for the predecessor, and linking an action to a second record.
- Migration downgrade and re-upgrade, and downgrade refused once reopenings exist.

`api/tests/test_issue_m3_assessment_revision_expand.py` now expects the two new keys in the assessment response. `test_issue_m3_presentation_correction.py` now downgrades to `0013` explicitly, because `-1` is `0015`.

Frontend: 60 tests pass, including a new reopening and revalidation flow.

Local gates: 197 API tests, 74 catalog tests (15 optional skips), 60 frontend tests, Ruff, Mypy, TypeScript typecheck, ESLint, and production build all passed. A clean `alembic upgrade head`, `downgrade -1`, `upgrade head` cycle also passed.

## Browser evidence

`prepare_synthetic_browser_fixture.py` builds three projects: A is reopened, revalidated, and reissued; B is issued and ready to reopen (second client); C is reopened with revalidation pending. The build was captured in **headless Chromium in the cloud container, not Edge on the Surface**, at 1600×1000 and 1280×720:

- `CHROMIUM_AFFECTED_SOURCE_SELECTION_*`: reopen form
- `CHROMIUM_NEEDS_REVALIDATION_*`: revalidation panel, remaining count
- `CHROMIUM_BLOCKED_CLOSE_*`: close blocked, generation blocked
- `CHROMIUM_SUPERSEDED_HISTORY_*`: superseded earlier revision with the current issue
- `CHROMIUM_PROJECT_SWITCH_*`: Project B after the switch, no Project A package IDs

No horizontal overflow at either width. One 404 resource load on the desktop first page load, not investigated; the response listener did not capture a URL.

Not done: a visible Edge run on the Surface. Delayed-response isolation is covered by the existing frontend suite and was not injected here.

## Known limits

- The system records who selected the affected records and why, but cannot prove an unselected record is unaffected. This is by design (ADR 0018) and is a practitioner judgement.
- `reopen` copies the assessment-scoped state of the whole assessment. A project with very large state will copy it all in one transaction.
