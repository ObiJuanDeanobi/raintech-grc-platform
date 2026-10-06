# Issue #100 template versioning verification

October 6, 2026. Synthetic data only. Branch `claude/issue-100-template-versioning` from `main` at `57ec650`.

## What changed

- `api/generation.py` keeps a registry, `TEMPLATE_VERSIONS`, mapping each version to its immutable folder and files, plus `CURRENT_TEMPLATE_VERSION`. New packages, including presentation corrections, render with the current version and record it in the package and manifest.
- Generation refuses to render with a version whose bytes differ from what any **issued** package recorded. The error says to publish the change as a new template version. A version no issued package has used can still change.
- Review binds each package to its **own** version's files, so a newer version never puts drift on an older package.
- The source content hash ignores `template_version`, so a correction from an unchanged source still passes when the current template version has moved on.
- The pre-issue backup now includes every template version, as `template/<version>/…`. Recovery already restores nested paths.

## How to publish a template change

1. Copy `docs/templates/hipaa/v2` to a new folder (for example `v3`). Make the change, and record its approval in that folder's `APPROVAL_RECORD.md`, following the sanitization gate.
2. Add the version to `TEMPLATE_VERSIONS` and set `CURRENT_TEMPLATE_VERSION`.
3. Never edit a folder an issued package has used. Generation will refuse to render with it.

## Evidence

`api/tests/test_issue_m3_template_versioning.py` has 3 tests:
- editing an issued version in place blocks generation and correction, with no new package
- an unissued version can still change
- a new `hipaa-v3` corrects a `hipaa-v2` issue: the old package's review has no drift, the backup holds both versions, the correction issues, and both packages keep their versions

Local gates: 200 API tests, 74 catalog tests (15 optional skips), 60 frontend tests, Ruff, Mypy, TypeScript typecheck, ESLint, and build all passed. No migration and no UI change.
