# Windows ARM64 package verification

- Date: September 21, 2026
- Branch: `feature/32-windows-acceptance`
- Starting checkpoint: `42adc3b`
- Host: Windows 11 Business 10.0.26200, ARM64

## Result

The production application built as a native ARM64 PyInstaller onedir package
and passed the maintained isolated verifier.

| Check | Result |
| --- | --- |
| Package | `RainTechGRC-windows-arm64.zip` |
| SHA-256 | `98FECD87424AEEEDDA797B859D7949A41AFDBF60844C536AEEE7437AD75D4B9F` |
| PE architecture | ARM64 (`0xAA64`) |
| ZIP size | 24.9 MiB |
| Cold health readiness | 2,235 ms |
| Restart health readiness | 2,031 ms |
| Compiled browser UI | HTTP 200 with application root |
| Isolated writable database | Pass |
| Synthetic client write | Pass |
| Persistence after graceful restart | Pass |
| Non-loopback connections | 0 |
| Authenticode status | NotSigned |
| Packaged recovery executable | Pass |

The verifier extracted the package to a disposable directory, set an isolated
`RAINTECH_DATA_DIR`, launched `RainTechGRC.exe` directly, created a synthetic
client through the packaged API, shut down through the application endpoint,
restarted, and confirmed the client remained present. The disposable data was
removed after verification. No live engagement workspace was read or changed.

## Remaining acceptance

- Complete the remaining late-stage package-review and issuance portion of the
  visible synthetic HIPAA walkthrough.
- Repeat with the network adapter disabled.
- Record downloaded-file SmartScreen behavior.
- Build and verify the package on native Windows x64 hardware.
