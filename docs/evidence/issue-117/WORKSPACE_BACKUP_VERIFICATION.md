# Issue #117 — Workspace backups, retention, and pre-migration backup

October 6, 2026. Synthetic data only.

## Behaviour

- **Back Up Now** (`POST /api/backups`): a full `raintech-recovery-set-v1`
  archive under `<backups>/workspace/`. It holds the database, managed files,
  templates, `application.json`, and a hashed manifest. Secret-like files are
  refused, as in the pre-issuance backup.
- **Automatic sets**:
  - **Daily** holds the database and metadata. It is due once per UTC day, and
    only after an audited change since the last daily set.
  - **Weekly** is full. It is due after a change, and at least 7 days after
    the last weekly set.
  - The packaged app (`api/windows_launcher.py`) and the module-level `app`
    check every 15 minutes and at startup. `create_app()` leaves the loop off
    by default, so tests and embedded uses don't race it.
- **Retention**: at most 14 daily and 2 weekly sets are kept. Pruned sets keep
  their record with status `pruned`. Manual sets and pre-issuance
  `backup_records` are never pruned.
- **Warning**: if the latest automatic daily or weekly attempt failed,
  `GET /api/backups` returns a warning until the next success. The top bar shows
  it as "Backup failed".
- **Pre-migration**: when the stored schema is behind head, `Database.migrate()`
  first copies the database to `files/backups/pre-migration/` and checks its
  integrity. If the copy fails, the migration does not run.
- **Restore**: unchanged. `api/recovery.py` restores any of these sets
  all-or-nothing into a new directory.

## Automated

`api/tests/test_issue_117_workspace_backups.py` (5 tests):

- Back Up Now, then `recover()`. The restored workspace opens with the project
  and its evidence file.
- The due rules: nothing before the first change, then daily and weekly.
  Nothing more on the same day. Daily again the next day; weekly again after
  8 days. A daily set holds only the database and metadata.
- Retention after 16 daily, 3 weekly, and 1 manual run: 14 and 2 are kept,
  2 and 1 pruned, and the manual set stays. Files on disk match the kept
  records.
- A failed daily warns until the next success.
- A pending migration creates one pre-migration copy at the old revision. A
  blocked copy stops the migration and leaves the schema unchanged.

A frontend test covers the warning chip and "Back up now".

Local results:

- `pytest`: 224 passed
- catalog `unittest`: OK
- frontend: 64 passed (three consecutive runs)
- Ruff, Mypy, typecheck, and ESLint: clean

I also ran a manual check: restarting an app with existing data and the loop
enabled produced one complete daily set and one complete weekly set.

## Not covered

- Monthly restore testing on the target Windows installation (AC-021) needs
  the Surface.
- No screenshots were taken; the UI change is one top-bar control, covered by
  the frontend test.
