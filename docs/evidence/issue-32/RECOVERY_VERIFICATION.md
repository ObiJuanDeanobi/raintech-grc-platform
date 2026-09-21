# Isolated recovery verification

Date: September 21, 2026

Recovery validation now rejects unsafe or duplicate archive paths, archive and
manifest mismatches, item size/hash failures, incompatible application metadata,
SQLite integrity failures, schema-version mismatches, and nonempty destinations.
Restore is staged beside the destination and published only after every check
passes. Failed validation removes staging and never publishes a partial target.

A focused integration test created a real recovery ZIP through the production
backup API, restored it into a clean directory, ran SQLite integrity checking,
confirmed the generated package remained in the restored database, and verified
managed files and recovery metadata were present.

Both portable packages include `RainTechGRCRecovery.exe`. The native ARM64 tool
and x64 tool under ARM64 emulation each restored a validated synthetic recovery
set into a new isolated directory without Python or Node installed as a runtime
requirement for the tool.

Focused result: 9 tests passed across recovery validation and production backup
integration. Ruff and Mypy passed.
