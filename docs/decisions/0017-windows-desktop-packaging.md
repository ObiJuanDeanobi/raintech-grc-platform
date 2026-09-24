# ADR 0017 - Package the Windows workspace as one local process

## Status

Accepted for the Windows offline pilot.

## Decision

RainTech GRC is distributed as separate native ARM64 and x64 portable packages.
Each package contains a windowless `RainTechGRC.exe` that runs one FastAPI
process on loopback, serves the compiled React UI, and opens the default browser.
Vite, Node, and a separately installed Python runtime are build-time concerns,
not target-machine requirements.

Read-only application resources remain in the package. The SQLite database,
managed files, backups, generation staging, and launcher log live beneath
`%LOCALAPPDATA%\RainTech\GRC Platform`. Builds use a short path beneath
`%LOCALAPPDATA%\RainTechGRC\build` and must be produced by a Python runtime that
matches the target architecture because PyInstaller does not cross-compile.

The first pilot package is portable and unsigned. Downloaded-file SmartScreen
behavior and public-trust signing remain explicit release decisions before
external distribution.

## Consequences

- A normal launch requires no elevation and starts only one application process.
- Mutable engagement data never lives beside the executable.
- ARM64 and x64 builds and acceptance evidence are maintained separately.
- The package verifier uses an isolated data root and proves UI/API health,
  persistence across restart, executable architecture, and loopback-only use.
- Native x64, adapter-disabled operation, browser walkthrough, Defender and
  SmartScreen behavior, and recovery rehearsal remain required acceptance gates.
