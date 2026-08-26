# Issue 61 verification record

Date: 2026-08-26  
Branch: `feature/61-profile-readiness-gate`  
Base: `0193c0c`  
Data: synthetic only

## Review state

Issue 61 is implemented and its independent-review findings are remediated.
This record is local implementation evidence, not an independent Standards or
Spec re-review PASS. No commit, push, pull request, merge, issue closure, or
Issue 62 work was performed.

## Test-first evidence

### Backend red

Initial command:

```text
.venv/bin/pytest api/tests/test_issue_61_profile_readiness.py -q
```

Result: 4 failed. The expected profile-readiness routes returned 404 and the
unmigrated database did not contain `projects.profile_readiness_state`.

### Backend green

Final focused result:

```text
5 passed
```

The focused suite covers the exact four states, declaration-driven transitions
and thresholds, readiness gates, boundary
acknowledgement wording, unresolved-field follow-up, named review evidence,
existing-assessment readability after regression, two-project isolation,
restart persistence, append-only and transition-continuity enforcement, actor attribution, and a
populated 0003 → 0004 → 0003 → 0004 migration cycle.

### Independent-review remediation red

Before remediation, the expanded backend suite produced `1 passed, 4 failed`:
Needs follow-up accepted blank follow-up work; direct Project-state mutation did
not fail; behavior did not consume the revised persisted declaration; and the
migration still added a mutable Project-state column.

The two added React regressions initially failed: the follow-up textarea was not
required, and the delayed Project-A reload scenario required a selector
correction before it could exercise the stale callback. After that test-only
correction and the application fixes, both focused React cases passed.

### Frontend red

Initial focused command:

```text
npm test -- --run web/src/App.test.tsx -t "shows readiness state"
```

Result: 1 failed. The application did not yet render the readiness gate and an
expected missing assessment produced an unhandled request path.

### Frontend green

Final result:

```text
22 passed
```

The frontend suite includes the blocked no-assessment state, mandatory
Needs-follow-up work, the controlled delayed-response two-project race, and
verification that a previously created assessment remains readable while the
project is in Needs follow-up.

## Migration and persistence

- Alembic reports one head: `0004`.
- Migration 0004 was generated additively and adds one project-scoped
  acknowledgement table, one project-scoped transition table, append-only
  update/delete triggers, a continuity trigger, and a project/timestamp index.
- Current state is derived from the latest append-only transition; there is no
  independently mutable `projects.profile_readiness_state` column.
- Existing projects are initialized at Intake started with an attributed
  initialization transition.
- A populated 0003 database containing an existing assessment was upgraded,
  downgraded, and re-upgraded. The assessment remained present and readable.
- Restart tests reopened the same SQLite database and retained readiness state,
  acknowledgement, transition history, and assessment readability.
- Direct attempts to update or delete transition rows failed with the
  append-only trigger.
- A direct attempt to mutate the removed Project-state column failed, and a
  direct discontinuous ledger insert failed with the continuity trigger.
- Two synthetic projects retained independent state, acknowledgement, history,
  and assessment-entry behavior.

Focused persistence command:

```text
.venv/bin/pytest \
  api/tests/test_issue_61_profile_readiness.py::test_populated_0003_migration_upgrade_downgrade_and_reupgrade \
  api/tests/test_issue_61_profile_readiness.py::test_two_project_isolation_restart_persistence_and_append_only_history \
  -q
```

Result: `2 passed`.

## Browser walkthrough

The final remediation walkthrough used Chromium at 1440×900 and the approved
minimum 1280×720 viewport against an isolated synthetic SQLite database.

1. Created `Synthetic Issue 61 Client · Synthetic Profile Readiness`.
2. Confirmed Intake started showed a concrete blocking reason and disabled
   Start assessment.
3. Confirmed the boundary path and the explicit statement that acknowledgement
   is not an attestation that content is free of CUI, PHI, or ePHI.
4. Acknowledged the boundary as Johnathan.
5. Recorded Intake complete with unknown required field `Security officer` and
   explicit follow-up work.
6. Confirmed assessment entry became available while Profile complete remained
   blocked.
7. Started the assessment.
8. Regressed readiness to Needs follow-up.
9. Confirmed the existing assessment remained readable and the assessment
   surface displayed the new-entry blocking reason.
10. Cleared the unresolved field and recorded Profile complete with
    `Synthetic Reviewer` and synthetic approval evidence.
11. Restarted the API, reopened the browser, and confirmed Profile complete,
    reviewer/evidence, and the existing assessment persisted.

Final browser checks reported no console errors, page errors, or HTTP responses
with status 400 or higher. The 1280×720 pass had no horizontal page overflow.
The Intake-complete capture was replaced from the corrected tree and its Next
state control contained only `Needs follow-up` and `Profile complete`.

The required `pplx-tool js_repl` browser bridge was described before use, but
the environment returned `tool_not_allowed` because `js_repl` was unavailable.
The same installed Playwright/Chromium runtime was therefore used directly as
the narrow fallback; this is a tooling limitation, not a product failure.

### Screenshots

- `desktop-intake-started.png` — Intake started, concrete assessment blocker,
  boundary wording, and profile-completion blockers at 1440×900.
- `desktop-intake-complete-follow-up.png` — corrected Intake complete capture
  with an explicitly tracked unknown field, follow-up work, and only valid next
  states at 1440×900.
- `minimum-existing-assessment-follow-up.png` — existing assessment readable
  during Needs follow-up, with the blocking reason visible at 1280×720.
- `desktop-profile-complete.png` — completed profile, named reviewer, approval
  evidence, and existing-assessment state at 1440×900.

## Final automated checks

Executed in one final run:

```text
.venv/bin/alembic heads
.venv/bin/pytest api/tests/test_issue_61_profile_readiness.py -q
.venv/bin/pytest \
  api/tests/test_issue_61_profile_readiness.py::test_populated_0003_migration_upgrade_downgrade_and_reupgrade \
  api/tests/test_issue_61_profile_readiness.py::test_two_project_isolation_restart_persistence_and_append_only_history \
  -q
.venv/bin/pytest api/tests -q
npm test -- --run web/src/App.test.tsx -t "requires explicit work|late Project A"
npm test
.venv/bin/ruff check api migrations
.venv/bin/mypy api
npm run typecheck
npm run lint
npm run build
.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
git diff --check
```

Results:

- Alembic: `0004 (head)`
- Focused backend: `5 passed`
- Focused populated migration/direct integrity: `2 passed`
- Focused React remediation: `2 passed` (`20 skipped`)
- Full backend: `22 passed`
- Full frontend: `22 passed`
- Ruff: all checks passed
- mypy: no issues in 9 source files
- TypeScript: passed
- ESLint: passed
- Vite: 1580 modules transformed; production build completed
- Catalog: 74 tests run, 15 skipped, OK
- `git diff --check`: passed

The backend warnings are the existing FastAPI/Python 3.14
`asyncio.iscoroutinefunction` deprecation warnings.

## ARM64/x64 source compatibility review

The Issue 61 diff adds no dependency or lockfile changes, native extensions,
architecture checks, platform-specific paths, shell launch behavior, scanner,
or hosted service. It uses the existing Python, SQLite, Alembic, FastAPI,
React, and browser APIs. A search of changed source found no `x86_64`, `amd64`,
`aarch64`, `arm64`, `platform.machine`, `os.uname`, or `sys.platform` branches.
The source is therefore architecture-neutral for ARM64 and x64; Windows
launcher and package execution remain outside this issue.

## Scope exclusions confirmed

No detailed profile schema or profile files, scanner, CUI/PHI/ePHI attestation,
upload warning, authentication/RBAC, hosted mode, backup/recovery, launcher, or
Issue 49 behavior was added or changed.
