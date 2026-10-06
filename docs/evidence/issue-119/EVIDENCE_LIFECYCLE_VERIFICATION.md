# Issue #119 — Evidence replace, recycle bin, and overdue review

October 6, 2026. Synthetic data only.

## Behaviour

- **Replace** (`POST /api/projects/{p}/evidence/{a}/versions`):
  - Appends an immutable version with its own SHA-256 and its own storage key,
    so version 1's bytes are never overwritten.
  - Existing mappings stay pinned. Record detail shows each mapping's pinned and
    latest version.
  - "Use latest version" (`PUT …/evidence-mappings/{m}/version`) is explicit,
    audited, and limited to the active assessment.
  - The evidence list shows the latest version.
- **Recycle bin:**
  - Only unmapped evidence can be binned (`POST …/recycle`).
  - A trigger refuses new mappings to binned evidence.
  - `POST …/restore` brings it back.
  - `DELETE …/evidence/{a}` purges stored bytes only from the bin. Artifact and
    version rows, including hashes, remain.
  - Purging is refused while a source snapshot, package manifest, or validation
    event cites any version, by id, hash, or path. Every generated package's
    source snapshot records the project's evidence versions.
  - Backups are self-contained archives and do not block purging.
- **Review date** (`PUT …/review-date`): evidence past its date is flagged
  `overdue` in lists and mappings. No determination changes.
- **Migration `0018`** adds `deleted_at`, `purged_at`, and `review_date`, plus
  the mapping trigger. Downgrade is refused while binned evidence exists.

## Automated

`api/tests/test_issue_119_evidence_lifecycle.py` (6 tests):

- **Replace keeps a Met determination and its v1 mapping.** Both files exist
  on disk. An explicit move updates the mapping; a second move returns 409.
- **Recycle bin:**
  - Mapped evidence cannot be binned.
  - Unbinned evidence cannot be purged.
  - Binned evidence leaves the main list, cannot be mapped, can be restored,
    and can be purged. Hash rows remain after purging.
- **Purge guard:** purging is refused after a real package generation cites
  the evidence, and the bytes remain.
- **Overdue:** the flag is set without changing Met.
- **Isolation:** guessed IDs from another project return 404 on every route.
- **Migration:** a 0018 cycle, plus the downgrade guard.

Two existing assertions changed:

- An exact-dictionary check now includes `review_date` and
  `latest_version_number`.
- The #117 pre-migration file-name check no longer hard-codes the head
  revision.

The frontend test covers "Version 2 is available" → "Use latest version", the
overdue notice, and restoring from the recycle bin.

Local results:

- `pytest`: 230 passed
- catalog `unittest`: OK
- frontend: 65 passed (three consecutive runs)
- Ruff, Mypy, typecheck, ESLint, and build: clean

## Deferred

- Archive, compress, and deduplicate. The specification says "where
  practical".
- Recurring-review notifications.
- No screenshots were taken. The UI additions are small controls inside the
  existing evidence panel, covered by the frontend test.
