# Windows ARM64 package verification

Date: September 18, 2026  
Branch: `feature/32-windows-acceptance`  
Starting checkpoint: `42adc3b`  
Host: Windows 11 Business 10.0.26200, ARM64

## Result

The production application built as a native ARM64 PyInstaller onedir package
and passed the maintained isolated verifier.

| Check | Result |
| --- | --- |
| Package | `RainTechGRC-windows-arm64.zip` |
| SHA-256 | `7F6B61762A0D857BFCF218C5BA464B1208AD38D068D48B6DF3FA1576B37E1FBE` |
| PE architecture | ARM64 (`0xAA64`) |
| ZIP size | 22.1 MiB |
| Cold health readiness | 2,658 ms |
| Restart health readiness | 2,048 ms |
| Compiled browser UI | HTTP 200 with application root |
| Isolated writable database | Pass |
| Synthetic client write | Pass |
| Persistence after graceful restart | Pass |
| Non-loopback connections | 0 |
| Authenticode status | NotSigned |

The verifier extracted the package to a disposable directory, set an isolated
`RAINTECH_DATA_DIR`, launched `RainTechGRC.exe` directly, created a synthetic
client through the packaged API, shut down through the application endpoint,
restarted, and confirmed the client remained present. The disposable data was
removed after verification. No live engagement workspace was read or changed.

## Remaining acceptance

- Complete the visible browser walkthrough for the full synthetic HIPAA flow.
- Repeat with the network adapter disabled.
- Exercise backup validation and restore rehearsal in an isolated location.
- Record Defender and downloaded-file SmartScreen behavior.
- Build and verify the package on native Windows x64 hardware.
