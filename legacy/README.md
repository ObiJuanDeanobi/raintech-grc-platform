# Legacy Material

Everything in this directory is preserved reference material, not active
production code.

```text
evidence-tracker/       Prior FastAPI/SQLite tracker and platform shell
prototypes/             Prior standalone HTML tools and visual concepts
github-bootstrap-v0/    Obsolete backlog seed and repository bootstrap scripts
local-artifacts/        Ignored local ZIP snapshots
```

The legacy tracker continues to use the workspace-level ignored `data/` folder
when launched through `legacy/evidence-tracker/run.ps1`.

Do not copy legacy modules into the fresh application wholesale. Reuse validated
behavior and tests only when an approved vertical slice calls for it.
