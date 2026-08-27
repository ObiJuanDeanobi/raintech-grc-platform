# Issue #62 verification

Status: implemented and locally verified. Initial, final, conclusive,
definitive, final-independent, and closure reviews reported High/Medium
findings; all reported findings are remediated locally and await another
independent re-review. No review PASS is claimed.

Branch and base:

- Branch: `feature/62-versioned-project-profile`
- Required base: `030096fc40174a48f18edf4389968dea726a46dd`
- No commit, push, pull request, merge, issue closure, deployment, or later
  milestone work was performed.

## Red/green evidence

Backend red:

- Command:
  `.venv/bin/pytest -q api/tests/test_issue_62_versioned_profile.py`
- Initial result: `4 failed`; the Profile routes and typed mapping columns did
  not yet exist.
- Raw output: `/home/user/workspace/issue62_backend_red.txt`

Backend green:

- Focused command:
  `.venv/bin/pytest -q api/tests/test_issue_62_versioned_profile.py`
- Result before review remediation: `5 passed`.
- Review-remediation red result: `7 failed` after adding destination-row,
  actor, stable-upload-ID, successor-mapping, inventory, and direct-SQL
  adversarial tests. Raw output:
  `/home/user/workspace/issue62_review_remediation_red.txt`.
- Closure-remediation green result: `28 passed`. This includes exact draft
  revision conflicts, active-pointer clear/rewind probes, canonical target
  uniqueness and delimiter probes, mapped destination identity guards,
  environment movement/retype/delete guards, environment-first successor
  cloning, failed-upload storage cleanup, whole-snapshot evidence revision
  conflicts, direct-SQL content invalidation, lifecycle revision attribution,
  unconditional pre-approval pointer checks, database-verifiable lifecycle
  revisions, immutable evidence display snapshots, and Alembic-style
  connection ledger-write denial.

Frontend red:

- Command:
  `./node_modules/.bin/vitest run web/src/ProfilePanel.test.tsx`
- Initial result: suite failed because `./ProfilePanel` did not exist.
- Raw output: `/home/user/workspace/issue62_frontend_red.txt`

Frontend green:

- Focused command:
  `./node_modules/.bin/vitest run web/src/ProfilePanel.test.tsx`
- Result before review remediation: `4 passed`.
- Final post-remediation green result: `16 ProfilePanel tests passed`,
  including exact revision submission and stale-conflict reload, canonical
  selector deduplication, dirty version-switch confirmation, two-environment
  nesting, delayed save with a newer local edit, evidence-revision adoption,
  delayed lifecycle/reuse/upload success with newer same-version local edits,
  and delayed lifecycle, reuse, upload, and successor responses after project
  switching.

## Automated checks

Executed after the final implementation:

| Check | Exact result |
|---|---|
| Full API tests: `.venv/bin/pytest -q` | `50 passed` |
| Catalog tests: `python -m unittest discover -s tests -v` | `74 tests`, `OK` |
| Ruff: `.venv/bin/ruff check .` | `All checks passed!` |
| Mypy: `.venv/bin/mypy catalog api` | `Success: no issues found in 14 source files` |
| TypeScript: `./node_modules/.bin/tsc --noEmit` | PASS, no diagnostics |
| ESLint: `./node_modules/.bin/eslint web` | PASS, no diagnostics |
| React tests: `./node_modules/.bin/vitest run` | `39 passed` |
| Vite build: `./node_modules/.bin/vite build` | PASS; 1,581 modules transformed |
| Git whitespace: `git diff --check` | PASS, no output |

The API test run reports upstream FastAPI/Python 3.14 deprecation warnings for
`asyncio.iscoroutinefunction`; they are warnings, not Issue #62 failures.

The conclusive review probes were also rerun after updating them to submit the
required revision:

- specification probe: mapping `201`, revision changed, stale review `409`;
- standards probe: mapping `201`, stale review after mapping `409`, stale review
  after direct-SQL content change `409`, and invalid pre-approval pointer
  blocked by `sqlite3.IntegrityError`.
- definitive Standards probe: caller-written revision authority was blocked by
  `sqlite3.IntegrityError` and the lifecycle remained `Draft`.
- final-independent arbitrary-token probe: caller ledger insertion/review was
  blocked and lifecycle remained `Draft`;
- final-independent restore probe: old-token reinsertion was blocked and normal
  stale lifecycle API review returned `409`.
- closure Alembic-style probe: direct insertion of a valid computed generation
  was blocked with `DatabaseError('not authorized')`, and ledger count remained
  `1`.

## Migration, persistence, and preservation

Clean migration cycle:

1. Upgrade an empty SQLite database from base through `0005`.
2. Downgrade from `0005` to `0004`.
3. Re-upgrade to `0005`.
4. Result: `clean upgrade/downgrade/re-upgrade: PASS`.

Populated migration coverage is in
`test_populated_0004_upgrade_downgrade_reupgrade_preserves_existing_workspace`.
It begins at `0004` with an existing project, assessment, artifact,
EvidenceVersion, assessment EvidenceMapping, prompt answer, prompt-move
rejection, and audit event. It verifies that:

- upgrade backfills the typed target as `assessment_record`;
- the original EvidenceVersion is referenced without rewriting its hash;
- one initial draft Profile version is backfilled for the project;
- downgrade restores the original assessment-mapping shape;
- assessment mapping rationale, prompt answer, rejection history, and audit
  event survive downgrade;
- re-upgrade restores the typed assessment target.

Restart coverage verifies active Profile pointer, immutable version content,
lifecycle, provenance, Profile mappings, and actor-attributed audits after
constructing a new application instance over the same database and storage
root.

Adversarial database and API coverage additionally verifies:

- item/value updates validate both old and new version status and fail closed
  when no lifecycle row exists;
- `content_revision` is a deterministic SHA-256 derived by the registered
  `profile_snapshot_revision()` SQLite function from the complete Profile
  snapshot; content triggers append only that database-derived value;
- `(profile_version_id, revision_token)` is unique, ledger UPDATE/DELETE is
  blocked, arbitrary caller tokens fail validation, and returning content to a
  prior displayed token cannot restore old authority;
- application, configured-test, and default Alembic-style registered
  connections install the same trigger-only ledger-write authorizer; raw
  unregistered connections fail closed because the snapshot function is absent;
- Alembic temporarily enables ledger bootstrap only inside the migration run,
  then reinstalls the default authorizer before releasing its connection;
- every field save, evidence reuse, upload, mapping update, and mapping delete
  requires the displayed revision under a write lock, returns the new revision,
  and rejects stale clients with `409`; React adopts successful revisions and
  reloads conflicts for re-review;
- lifecycle UPDATE and DELETE are rejected as append-only;
- Reviewed and Approved lifecycle ledger rows persist the exact snapshot
  revision reviewed by the named reviewer;
- Reviewed/Approved rows must match both the latest validated ledger token and
  an independent live `profile_snapshot_revision()` recomputation; summary
  columns are immutable and are not an authorization source;
- approval insertion updates the active pointer in the same database operation;
- direct SQL cannot clear or rewind the active pointer while an approved
  lifecycle ledger exists;
- before the first approval, direct SQL cannot set the pointer to a draft,
  nonexistent, cross-project, or arbitrary value, including during project
  insertion;
- artifact, EvidenceVersion, mapping, Profile version, and assessment ownership
  are tied to one project with composite foreign keys;
- an EvidenceVersion cannot be paired with a different artifact;
- Profile mapping targets resolve to existing canonical top-level or item field
  identities in that exact version; API validation, database constraints, and
  React selector deduplication keep each canonical target one-to-one and reject
  delimiter collisions;
- mapped field identity cannot be deleted or moved behind the mapping;
- mapped item keys cannot change, and referenced environments cannot be deleted,
  retyped, or moved;
- mapping update/delete loads and validates the destination row by its own
  project, target type, and Profile version under a write lock;
- cross-project deletion, same-project wrong-version mutation, and
  reviewed/approved-version mutation return controlled `404`/`409` responses
  without changing the row;
- trigger-raised `sqlite3.IntegrityError` returns a controlled `409`, including
  field, lifecycle, successor, and mapping trigger paths;
- nonexistent Profile actors return `422` before rows, files, mappings, or
  audits are written;
- same-name uploads receive distinct server-generated `uploaded_file_id`,
  artifact, path, and mapping identities while retaining the original filename;
- a forced post-write Profile mapping failure leaves no artifact/mapping rows
  and no staged or final managed-storage bytes;
- Profile mappings snapshot `artifact_name` and `uploaded_file_id`; approved
  Profile display and revision do not change when the live artifact row changes;
- successor versions clone independent mapping rows to the same immutable
  EvidenceVersion and hash, inserting environments before dependent inventory
  while preserving the original display `sort_order`.

## Browser walkthrough

The walkthrough used only synthetic, sanitized bytes and synthetic HIPAA/CMMC
projects. It exercised:

- a HIPAA draft through Reviewed and Approved;
- creation of a later draft while prior approved snapshots remained readable;
- per-value source, reviewer, and last-reviewed fields;
- all neutral Profile sections and environment-grouped inventory;
- canonical Profile target selectors rather than free-text target identities;
- same-project reuse of an existing EvidenceVersion;
- a new managed-local upload, visible immutable Version 1, and SHA-256;
- initial Profile mapping state `Not reviewed`;
- the pre-existing assessment mapping on the Risk Analysis record;
- cross-project Profile reads and mapping attempts returning `404` with the
  HIPAA Profile byte-for-byte unchanged at the API response seam;
- normal project switching from HIPAA to synthetic CMMC without HIPAA evidence
  appearing in CMMC;
- the same `ProfilePanel` and explicit no-template state for both projects.

React regression tests separately exercise exact revision submission,
stale-conflict reload/re-review, unsaved-draft review blocking, dirty Profile
version switching, navigation confirmation, unique canonical target options,
and stale mutation completion for save, lifecycle, reuse, upload, and successor
creation. A delayed save cannot overwrite a newer local edit or mark it saved.
The UI disables every Profile field/item editor and Profile version switching
for the full lifecycle request, then immediately applies the real
Reviewed/Approved response. Delayed reuse and upload merge mapping/revision
state exactly once through functional state without replacing newer fields or
items.
A late Project A or prior-version completion cannot place stale values,
versions, evidence, messages, or errors into the selected context.

Browser error result:

- console errors: `[]`
- page errors: `[]`
- unexpected network errors: `[]`

Minimum viewport result at `1280x720`:

- document width: `1280`
- horizontal overflow: `false`
- Profile title visible: `true`

Machine-readable browser result:
`/home/user/workspace/issue62_browser_report.json`.

## Screenshots

- `desktop-hipaa-neutral-draft.png` — neutral Profile form, Draft version,
  provenance, boundary language, and no-template state at `1440x900`.
- `desktop-environment-inventory-nested.png` — inventory rendered inside its
  selected environment with no unassigned state.
- `desktop-hipaa-profile-evidence.png` — same-project reuse and new stored-byte
  upload with visible Version 1 hashes and `Not reviewed` mappings.
- `desktop-hipaa-approved-prior-version.png` — immutable readable prior
  Approved version and Draft → Reviewed → Approved lifecycle.
- `desktop-assessment-mapping-regression.png` — the existing assessment-record
  mapping remains visible on HIPAA Risk Analysis.
- `minimum-cmmc-neutral-no-template.png` — synthetic CMMC project using the same
  neutral component at `1280x720`, with no released template.

## ARM64/x64 source compatibility review

PASS at the source level:

- no dependency was added;
- storage and hashing continue to use Python `pathlib`, file I/O, and
  `hashlib.sha256`;
- persistence remains SQLite/Alembic with no architecture-specific SQL,
  extension, native binary, shell command, or path separator;
- the React implementation uses existing React, browser `FormData`, and
  `lucide-react` dependencies only;
- no x64- or ARM64-specific code path, compiler flag, or package was introduced.

Native Windows packaging and hardware acceptance remain separately governed and
were not claimed here.

## Deferred and explicitly absent

No framework template, dynamic form builder, JSON Schema engine, template
compiler, ontology/crosswalk, authentication/RBAC, hosted/cloud storage,
OneDrive/network share, bulk import, content scanner/attestation/warning,
backup/recovery, evidence replacement, mapping review transitions, assessment
gate beyond Issue #61, Issue #49 behavior, or later milestone feature was added.
