# Windows pilot release gate

Date: September 24, 2026. Branch: `feature/32-windows-acceptance`.

## Current packaging verdict

**Proceed with named changes for pilot preparation.** The packaged synthetic
HIPAA flow, immutable retrieval, and isolated recovery passed on native ARM64.
The x64 package passed launch, restart, persistence, recovery, and loopback
checks under Windows-on-ARM emulation. This is a provisional architecture
verdict; Issue #32 and draft PR #92 remain open.

Before declaring Windows offline acceptance complete:

1. Run the x64 ZIP on native x64 Windows hardware, including the packaged
   entry point, recovery tool, restart, and issued-package retrieval.
2. Run the required flow with the host network adapter disabled in a physical
   session where doing so cannot sever the active development connection.
3. Observe downloaded-file SmartScreen behavior from the intended distribution
   channel. Local build execution cannot establish that result.

## Architecture dependencies

`packaging/windows/build.ps1` requires a matching Python architecture and
bundles the Python runtime, application, compiled UI, templates, catalog,
migrations, and recovery executable. The target computer needs neither Python
nor Node. Final ARM64 and x64 ZIP hashes and the exercised host are recorded in
`EDGE_BROWSER_VERIFICATION.md`; package verification results are in
`ARM64_VERIFICATION.md` and `X64_EMULATION_VERIFICATION.md`.

PyInstaller emitted unresolved Windows system DLL analysis warnings while
building x64 on ARM64. The x64 ZIP nevertheless passed the isolated verifier
under emulation. No missing runtime dependency was observed in those checks,
but native x64 compatibility is still unverified. The architecture dependency
criterion remains open until the native run resolves this uncertainty.

## Trust and signing decision

Both local packages are unsigned. Targeted Defender scans found zero
detections; `DEFENDER_VERIFICATION.md` records their scope. Downloaded-file
SmartScreen behavior is unknown. Whether signing is required for an ordinary
client download therefore remains a release decision after the distribution
channel check. If it is required, record certificate/provider cost, lead time,
key custody, signing and timestamp steps, and release-process impact before
changing the pilot distribution plan.
