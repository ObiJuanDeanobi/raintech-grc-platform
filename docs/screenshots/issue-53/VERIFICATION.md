# Issue 53 Verification Record

Date: 2026-08-24  
Branch: `feature/53-project-scoped-immutable-local-evidence`  
Fixed point: `6d79acdcd680ee1ef89a32eeeeefba38cd569986`

## Scope and data handling

All browser and automated verification used synthetic data. The browser fixture was a plain-text file containing only:

> Synthetic Issue 53 evidence artifact. No client or regulated data.

No CUI, PHI, ePHI, client evidence, or production data was used.

## Automated verification

The API integration suite verifies:

- direct upload into project-scoped managed local storage;
- creation of exactly one immutable initial `EvidenceVersion`;
- version number `1`;
- SHA-256 calculated from bytes read back from managed storage;
- initial mapping review state `Not reviewed`;
- same-project reuse with per-mapping rationale and review state;
- persistence across application restart;
- preservation and hashing of populated `0001` evidence during migration to `0002`;
- safe migration failure when a pre-existing artifact's managed bytes are unavailable;
- rejection of version update and delete operations;
- Project B isolation for evidence listing, record mapping, and assessment audit access.

The React integration suite verifies that the existing evidence panel displays the initial version, SHA-256, and review state without introducing a separate evidence-management workflow.

Final commands and results:

```text
.venv/bin/ruff check .                         passed
.venv/bin/mypy catalog api                     passed
.venv/bin/pytest                               9 passed
.venv/bin/python -m unittest discover -s tests 73 passed, 15 skipped
pnpm-compatible typecheck                      passed
pnpm-compatible lint                           passed
pnpm-compatible test                           12 passed
pnpm-compatible build                          passed
git diff --check                               passed
```

The frontend commands used the repository-compatible cached `pnpm@10.17.1` executable under Node 20 with package-manager version delegation disabled. The pinned pnpm 11 executable requires Node 22.13 or later; no dependency or lockfile change was made.

## Migration verification

A temporary SQLite database completed this sequence successfully:

1. Upgrade from base to `head`.
2. Downgrade from `0002` to `0001`.
3. Re-upgrade from `0001` to `head`.
4. Downgrade from `0002` to base.

This exercised creation and removal of the evidence-version table, mapping review-state column, indexes, uniqueness constraint, and immutable update/delete triggers.

Separate populated-workspace regressions prove that an existing `0001` artifact and mapping remain visible after upgrade, receive a correct version-1 SHA-256 from the managed bytes, and survive downgrade/re-upgrade. If the configured storage root is unavailable, a relative path escapes that root, or stored bytes are missing, migration stops before creating the version table instead of inventing provenance or silently hiding evidence.

## Browser walkthrough

The local FastAPI and Vite applications were exercised through Chromium at `1440 × 900`, followed by a viewport-fit check at `1366 × 768`.

### Project A

Using the direct file picker:

1. Uploaded `synthetic-issue-53-evidence.txt`.
2. Confirmed `Version 1`.
3. Confirmed SHA-256 `1c91f2494e0c79e43b92a50216875676d0f856290bde1f4a7bb1a25bb4c14172`.
4. Mapped the artifact to record 001 with a synthetic rationale.
5. Reused the same artifact on record 002 with a second synthetic rationale.
6. Confirmed `Not reviewed` and `Shared across 2 records`.
7. Reloaded the application and confirmed the version, hash, review state, and reuse count persisted.

Evidence: `project-a-versioned-evidence.png`

### Project B isolation

Using the normal `+ Client / project` workflow:

1. Created `Issue 53 Synthetic Isolation Project B`.
2. Confirmed the evidence selector contained only `Choose evidence…`.
3. Confirmed the Project A filename, version, and hash were absent.
4. Confirmed the mapped-evidence count was zero.

Evidence: `project-b-isolated.png`

No browser console errors occurred during upload, mapping, reuse, project switching, isolation checks, or reload.

## Viewport and compatibility review

At `1366 × 768`, the application had no page-level horizontal or vertical overflow. The right working-record pane remained independently scrollable, with the mapped-evidence region reachable inside that pane.

The change adds no dependency, lockfile, platform-specific path, native module, or shell integration. Hashing uses Python's standard `hashlib`, persistence uses the existing SQLite/Alembic stack, storage uses the existing Python local-file seam, and the UI uses the existing React/browser stack. Source review found no ARM64- or x64-specific implementation. Native Windows launcher/offline acceptance remains the separate human gate in Issue #32.

## Review state

Implementation and verification are complete. Both independent review axes
passed with no P0, High, or Medium findings. The next gate is repository CI on
the pull request; merge requires separate approval.
