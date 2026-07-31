# Windows Package Spike (Throwaway)

This directory exists only to answer GitHub Issue #32. It is not production
launcher code and must not be merged into `main`.

The spike packages the current FastAPI/SQLite service and the compiled React UI
as one local Windows application process. The executable serves the UI from
`127.0.0.1`, opens the default browser, and writes mutable data beneath the
current user's local app-data directory. No Vite or Python installation is
needed on the target after packaging.

Build on Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\prototypes\windows-package-spike\build.ps1 -Architecture arm64
powershell -ExecutionPolicy Bypass -File .\prototypes\windows-package-spike\build.ps1 -Architecture x64
```

Verify the packaged executable:

```powershell
powershell -ExecutionPolicy Bypass -File .\prototypes\windows-package-spike\verify.ps1 -Architecture arm64
powershell -ExecutionPolicy Bypass -File .\prototypes\windows-package-spike\verify.ps1 -Architecture x64
```

Create a disposable desktop shortcut:

```powershell
powershell -ExecutionPolicy Bypass -File .\prototypes\windows-package-spike\create-shortcut.ps1
```

The durable output of this spike is the written verdict on Issue #32, not this
code or its binaries. Temporary build environments and binaries are placed at
`%LOCALAPPDATA%\RainTech\PackageSpike` to stay below Windows' legacy path limit.
