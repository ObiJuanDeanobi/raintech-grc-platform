# ADR 0015: Local evidence integrity and recovery

## Status

Accepted. Approved by Johnathan on August 24, 2026 under GitHub issue #50.

## Context

The V1 platform is fully local and must preserve evidence integrity and recover
the complete working set without introducing a synchronized or cloud
destination. The regulated-data boundary also depends on operating practice,
not a content scanner or user attestation.

## Decision

V1 stores application data, evidence, templates, generated artifacts, manifests,
and backups on local storage selected by the operator. OneDrive, other
synchronized folders, and cloud backup destinations are rejected.

Every evidence version receives a SHA-256 value at ingestion. Verification
results are visible to the operator and travel with evidence indexes and
issuance manifests.

The operating documentation requires upstream sanitization and excludes CUI,
PHI, and ePHI from the platform. Development, fixtures, demonstrations, and
tests use sanitized or synthetic data. V1 does not add a content scanner or an
attestation prompt as a substitute for that boundary.

A successful full backup captures a complete recoverable set: database,
evidence and hash metadata, templates, generated artifacts, and manifests.
Daily database/configuration backups are distinct from that full recovery set.
Backup behavior includes:

- visible manual backup status;
- one daily backup after the first change, not after every edit;
- one weekly full backup;
- an upgrade blocked until its required pre-upgrade backup succeeds;
- retention of 14 daily and 2 weekly backups;
- rejection of synchronized or cloud destinations; and
- offline restore verification on representative ARM64 and x64 Windows systems.

## Consequences

Recovery claims require a complete-set contract and representative-machine
verification. Backup implementation cannot be folded into the launcher spike,
and cloud-session testing cannot prove Windows recovery.

## Traceability

REQ-004, REQ-014, and REQ-018 through REQ-020.
