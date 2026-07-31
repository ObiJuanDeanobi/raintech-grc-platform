# Issue #32 Spike Results

Date: 2026-07-31

Host: Microsoft Surface Pro, 11th Edition; Windows 11 ARM64.

## Verified

- Native ARM64 and x64 PyInstaller `onedir` packages were produced from the
  approved FastAPI, SQLite, React, and TypeScript stack. PE headers were checked
  directly: `0xAA64` for ARM64 and `0x8664` for x64.
- The native ARM64 package launched from a desktop shortcut, served the compiled
  React UI on `127.0.0.1`, created a synthetic client/project through the browser,
  and loaded the 149-record assessment workspace with no browser warnings or
  errors.
- The package wrote its database without elevation at
  `%LOCALAPPDATA%\RainTech\GRC Platform Spike\workspace.db`.
- A client write survived a forced process stop and restart for both packages.
- The clean shutdown endpoint exited the packaged process fully.
- No package dependency lacked an ARM64 wheel or binary. In particular,
  Pydantic Core and PyInstaller resolved native ARM64 wheels.
- While executing the read/write flows, the application opened zero
  non-loopback connections. All compiled UI assets were served from the package.
- Microsoft Defender Antivirus and real-time protection were enabled. A custom
  scan of the ARM64 package returned zero detections.

## Measurements

| Package | Host mode | Cold launch | Restart | Package size |
| --- | --- | ---: | ---: | ---: |
| ARM64 | native | 4.7 seconds | 3.4 seconds | 34.8 MiB |
| x64 | Windows 11 ARM64 emulation | 6.9 seconds | 4.5 seconds | 41.8 MiB |

The x64 package was not run on native x64 hardware because none was available in
this session.

## Findings

1. The production package should contain one application process. FastAPI serves
   the compiled React assets and opens the default browser; a separate Vite
   process is a development concern and adds no value to the installed app.
2. Separate native builds are required. PyInstaller follows the architecture of
   its Python environment and is not a Windows cross-compiler. Windows ARM64 can
   run the x64 build under emulation, but that is not a native ARM64 build.
3. Mutable data must not live beside the executable. The user-local app-data
   location worked without elevation and survived package rebuilds and crashes.
4. The repository's deep checkout exceeded Windows' legacy path limit twice:
   once during ARM64 packager installation and once during package collection.
   The short `%LOCALAPPDATA%\RainTech\PackageSpike` build root resolved both.
5. A windowless PyInstaller executable cannot use Uvicorn's default console
   logger. It raised an `isatty` exception because stdout was absent. Disabling
   Uvicorn's console logging and writing launch failures to a local file resolved
   it.
6. Both executables are unsigned. Local execution did not invoke SmartScreen
   because the files were locally built and had no internet-zone marker; this is
   not evidence that a downloaded unsigned release will be warning-free.

## Remaining hardware check

An actual adapter-disabled run could not be automated from the unelevated test
session. The stronger evidence available here is a complete packaged browser
read/write flow with all assets local and zero non-loopback connections. A brief
manual Wi-Fi-off launch should remain in the release checklist. Native x64
hardware launch should also remain in that checklist.

