# Windows packaging

This is the maintained packaging path for the **Windows Offline Pilot
Acceptance** work tracked in GitHub issue #32. It creates separate native x64
and ARM64 portable executable packages without touching live user data.

Run the build with a matching Python architecture, then validate the resulting
ZIP in an isolated workspace:

```powershell
.\packaging\windows\build.ps1 -Architecture arm64 -Python python -Clean
.\packaging\windows\verify.ps1 -Package .\dist\windows\RainTechGRC-windows-arm64.zip
```

The package includes its Python runtime, API, compiled browser UI, catalog and
version data, HIPAA v2 templates, migrations, and Alembic configuration. The
target computer does not need Python or Node. Mutable data defaults to
`%LOCALAPPDATA%\RainTech\GRC Platform`; `RAINTECH_DATA_DIR` overrides that path
for isolated verification.

The verifier checks health, a persisted synthetic write across restart,
executable architecture, signature state, package size, and loopback-only
connections. Native ARM64 and x64 packages must each be built with a matching
Python runtime because PyInstaller does not cross-compile. Production release
signing remains a separate release-control decision.
