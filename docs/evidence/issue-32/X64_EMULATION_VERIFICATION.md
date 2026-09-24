# Windows x64 package verification under ARM64 emulation

- Date: September 21, 2026
- Branch: `feature/32-windows-acceptance`
- Prior checkpoint: `ae67ca3`
- Host: Windows 11 Business 10.0.26200, ARM64

## Result

The production application built from an x64 Python 3.14 runtime and passed the
maintained isolated verifier under Windows x64-on-ARM64 emulation.

| Check | Result |
| --- | --- |
| Package | `RainTechGRC-windows-x64.zip` |
| SHA-256 | `33F737FD99347F6B01D4CAC0653B9148971144074EEFCE530D24E4FD02B64E5C` |
| PE architecture | x64 (`0x8664`) |
| ZIP size | 28.9 MiB |
| Cold health readiness | 4,180 ms |
| Restart health readiness | 2,540 ms |
| Compiled browser UI | HTTP 200 with application root |
| Isolated writable database | Pass |
| Synthetic client write | Pass |
| Persistence after graceful restart | Pass |
| Non-loopback connections | 0 |
| Authenticode status | NotSigned |
| Packaged recovery executable | Pass under emulation |

PyInstaller reported unresolved Windows system-DLL warnings while analyzing the
x64 runtime on an ARM64 host. The completed x64 package nevertheless launched
and passed the runtime verifier under Windows emulation. Native x64 hardware
verification remains required and is not inferred from this result.

The verifier used a disposable data directory and removed it afterward. No live
engagement workspace was read or changed.
