# Windows x64 package verification under ARM64 emulation

Date: September 21, 2026  
Branch: `feature/32-windows-acceptance`  
Prior checkpoint: `ae67ca3`  
Host: Windows 11 Business 10.0.26200, ARM64

## Result

The production application built from an x64 Python 3.14 runtime and passed the
maintained isolated verifier under Windows x64-on-ARM64 emulation.

| Check | Result |
| --- | --- |
| Package | `RainTechGRC-windows-x64.zip` |
| SHA-256 | `9C40D92CA8A6114C1276233E7EB3FCE22A76DC1CF106221F95ACFBDDAF7D7F06` |
| PE architecture | x64 (`0x8664`) |
| ZIP size | 20.2 MiB |
| Cold health readiness | 5,290 ms |
| Restart health readiness | 2,047 ms |
| Compiled browser UI | HTTP 200 with application root |
| Isolated writable database | Pass |
| Synthetic client write | Pass |
| Persistence after graceful restart | Pass |
| Non-loopback connections | 0 |
| Authenticode status | NotSigned |

PyInstaller reported unresolved Windows system-DLL warnings while analyzing the
x64 runtime on an ARM64 host. The completed x64 package nevertheless launched
and passed the runtime verifier under Windows emulation. Native x64 hardware
verification remains required and is not inferred from this result.

The verifier used a disposable data directory and removed it afterward. No live
engagement workspace was read or changed.
