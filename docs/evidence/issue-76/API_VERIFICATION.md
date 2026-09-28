# Issue #76 active-assessment service verification

September 28, 2026. Synthetic data only.

The service regression tests exercise the production FastAPI routes against isolated temporary SQLite databases and managed-file roots. Close and generation reject same-client and cross-client project IDs before reading assessment sources or writing snapshot, attempt, or package rows. A simulated inactive pointer rejects close, generation, package review, issue readiness, backup, and issuance; the latter checks leave backup and issuance tables unchanged. Package listing hides the inactive candidate, and its component download returns 404 before resolving a managed file path. Valid active package behavior remains covered by the existing generation, review, backup, issuance, and restart tests.

The current schema still permits only one assessment per project and protects its active pointer. To exercise an inactive package without enabling successors or changing production constraints, the regression tests alter only their disposable database fixture. Browser project-switching evidence for the active-assessment backend is recorded in `../issue-75/BROWSER_BACKEND_VERIFICATION.md`; #76 changes backend service and read-route behavior only.

Local verification: 159 API tests passed; 74 catalog tests passed with 15 optional skips; 52 frontend tests passed; Ruff, Mypy, TypeScript typecheck, ESLint, and production build passed. GitHub CI status is tracked in the PR and `PROJECT_STATUS.md`.
