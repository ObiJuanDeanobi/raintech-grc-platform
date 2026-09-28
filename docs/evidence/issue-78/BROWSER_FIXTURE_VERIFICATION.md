# Issue #78 synthetic browser fixture smoke

September 28, 2026. Synthetic data only.

`prepare_synthetic_browser_fixture.py` created a fresh local workspace under `C:\Users\johnathan\RainTechAcceptance\issue-78-browser-fixture`. It invoked the shared backend `create_workspace` helper for the first project and created one more project under that client plus one under a second synthetic client. All three projects had separate active assessment IDs and retained the production one-assessment constraint. The setup ran current Alembic migrations through head; it did not alter the existing packaged Surface pilot.

Run from the repository root with `PYTHONPATH=.`:

```powershell
& .\.venv\Scripts\python.exe docs\evidence\issue-78\prepare_synthetic_browser_fixture.py 'C:\Users\johnathan\RainTechAcceptance\issue-78-browser-fixture'
```

The script requires a new destination directory on each run. The repository frontend build was served on isolated port 18578 with that data directory. Visible Microsoft Edge opened the first 194-record HIPAA assessment, then selected the second project under the same client and the third project under another client. Each destination showed its own selected project and assessment work list; no prior-project answer, package, or record state appeared. `EDGE_FIXTURE_FIRST.png`, `EDGE_FIXTURE_SAME_CLIENT.png`, and `EDGE_FIXTURE_CROSS_CLIENT.png` capture those states. Edge reported zero console warnings or errors. The temporary verification server was stopped; the existing packaged app on port 18433 was untouched.

Test-only multi-revision selection is covered by `api/tests/test_issue_m3_active_assessment_fixtures.py`; the visible browser smoke uses the production schema with one revision per project until #79 enables successors.

Local gates: 167 API tests passed; 74 catalog tests passed with 15 optional skips; 58 frontend tests passed; Ruff, Mypy, TypeScript typecheck, ESLint, and production build passed. The recursive repository search guard runs in the API suite.
