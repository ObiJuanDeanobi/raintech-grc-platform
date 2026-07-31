# ADR 0013 - Package the Windows Desktop Workspace as One Local Process

## Status

Proposed

## Decision

Proceed with the approved stack, subject to Johnathan's approval of these
packaging constraints:

1. The installed application runs as one local process. FastAPI serves the
   compiled React assets on loopback and opens the default browser. Vite remains
   a development tool and is not a second installed process.
2. Produce separate ARM64 and x64 packages from native Python environments.
   PyInstaller follows the active Python architecture and [is not a
   cross-compiler](https://pyinstaller.org/en/stable/usage.html#supporting-multiple-operating-systems).
3. Store the SQLite database, managed files, configuration, and launcher logs
   beneath `%LOCALAPPDATA%\RainTech\GRC Platform`. Nothing mutable lives beside
   the executable or requires elevation.
4. Build at a short, predictable path or enable Windows long-path support in the
   build environment. The repository's deep checkout exceeded the legacy path
   limit during both ARM64 dependency installation and package collection.
5. A windowless executable disables Uvicorn's console logger and writes startup
   failures to the user-local log. The default logger assumes a console stream
   and failed when packaged without one.
6. Treat public-trust code signing as a release decision, not as a technical
   prerequisite for local execution. The unsigned local spike ran, but it did
   not test a downloaded file carrying an internet-zone marker. Microsoft says
   unsigned downloads can show a "Windows protected your PC" warning and
   recommends Artifact Signing for non-Store distribution. Before external or
   managed distribution, test the downloaded-file path and have Johnathan decide
   whether to require consistent signing. The current Basic plan is $9.99 per
   month for up to 5,000 signatures. Public identity validation takes 1 to 20
   business days and can take longer when Microsoft requests more documents.
7. Keep native ARM64 and native x64 launch, Wi-Fi-disabled read/write, forced
   close/restart, clean shutdown, Defender scan, and downloaded-file SmartScreen
   behavior in the release checklist. The spike directly proved ARM64 and x64
   under ARM64 emulation; native x64 hardware and an actual adapter-disabled run
   remain incomplete Issue #32 checks.

## Context

V1 must run locally without a login or internet connection on Windows ARM64 and
x64, open from a double-click launcher, and retain its SQLite workspace between
launches. The production stack is FastAPI, SQLite, React, and TypeScript. Issue
#32 tested that stack on a Windows 11 ARM64 Surface before later slices committed
to an unproved packaging assumption.

The spike reused the already-built Slice 1a workspace only as packaged test
input; it added no product features. Its throwaway code is temporarily captured
on branch `codex/issue-32-windows-package-spike` for review evidence and must
never merge. Delete that branch after this verdict is approved and merged.

The spike has reached a provisional **proceed with named changes** verdict. Two
ticket checks remain: native x64 hardware and actual networking-disabled
operation. The existing evidence does not close either check.

## Evidence

- Native ARM64 package: 34.8 MiB, 4.7-second cold launch, 3.4-second restart.
- x64 package under Windows 11 ARM64 emulation: 41.8 MiB, 6.9-second cold launch,
  4.5-second restart.
- Direct PE-header checks confirmed ARM64 (`0xAA64`) and x64 (`0x8664`).
- The desktop shortcut launched the native package and the clean shutdown path
  fully exited it.
- Browser creation of a synthetic client/project loaded the 149-record workspace
  with no browser warnings or errors.
- SQLite writes in the user-local path survived forced close and restart for
  both packages.
- No ARM64 dependency wheel or binary was missing. Pydantic Core and PyInstaller
  both resolved native ARM64 wheels.
- The running application opened zero non-loopback connections, and all UI
  assets were served from the package. This supports, but does not replace, the
  pending adapter-disabled test.
- Microsoft Defender Antivirus, with real-time protection enabled, reported no
  detection in a custom scan of the ARM64 package.
- Both local binaries reported `NotSigned`. No SmartScreen conclusion was drawn
  from locally built files because they lacked an internet-zone marker.

Microsoft references:

- [SmartScreen reputation for Windows app developers](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation)
- [Artifact Signing product and pricing](https://azure.microsoft.com/en-us/products/artifact-signing)
- [Artifact Signing setup, identity validation, and processing time](https://learn.microsoft.com/en-us/azure/artifact-signing/quickstart)

## Consequences

If accepted, the approved product architecture remains viable on Windows ARM64,
and the x64 build has no blocker under Windows 11 ARM64 emulation. Native x64
remains unverified. The production launcher becomes simpler because it owns one
application process rather than coordinating independent API and frontend
servers. Packaging becomes a repeatable per-architecture build concern, not a
current reason to change the application stack.

Public-trust signing remains a product-owner release decision with known cost
and lead time. Native x64, adapter-disabled operation, and downloaded-file
SmartScreen behavior remain explicit Issue #32 checks rather than being inferred
from the ARM64-host results.
