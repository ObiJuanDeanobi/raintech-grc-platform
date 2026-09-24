# Component and template drift gate tests

Focused API coverage added for the Issue #32 source/component/template drift criterion. The tests generate and sign synthetic packages in pytest temporary directories, then modify either a generated component or a copied approved template after sign-off. In both cases issue readiness reports the matching drift blocker and backup creation returns HTTP 409. The template test uses a copied repository fixture; no checked-in template or live acceptance data is modified.

Verification on the `feature/32-windows-acceptance` checkout:

```text
.venv\Scripts\python.exe -m pytest api/tests/test_issue_m3_hipaa_issue_backup.py -q
8 passed, 1 warning in 25.58s
```

The warning is the existing Starlette deprecation notice for `anyio.abc.BlockingPortal`.

Source drift is covered separately by
`test_backup_binding_drift_and_direct_sql_records_are_immutable` in the same
passing module: changing an authoritative determination after backup blocks
issuance. The visible packaged Edge walkthrough also showed an older stale
candidate blocked from sign-off and backup; see `EDGE_BROWSER_VERIFICATION.md`.
