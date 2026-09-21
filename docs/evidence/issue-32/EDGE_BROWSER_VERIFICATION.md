# Packaged Edge browser verification

- Date: September 21, 2026
- Branch: `feature/32-windows-acceptance`
- Host: Windows 11 Business 10.0.26200, ARM64
- Browser: Microsoft Edge through the installed browser-control extension

## Result

The rebuilt native ARM64 package was launched directly with an isolated data
root at `C:\Users\johnathan\RainTechAcceptance\edge-20260921`. The visible Edge
workflow passed these checks using synthetic data only:

- opened the compiled application at its loopback URL;
- created a client and HIPAA project;
- enforced the operating-boundary acknowledgement and reviewer-evidence gates;
- moved intake through `Intake complete` and `Profile complete`;
- started the pinned `hipaa-45cfr164-2026-07-01` assessment;
- displayed the complete 194-record HIPAA work list;
- saved a question-level answer and retained it after a full page reload;
- derived the question completion indicator from the persisted answer; and
- reported no browser console warnings or errors.

The first pass exposed a misleading uncontrolled question checkbox that reset
after reload even though its answer persisted. The checkbox is now a disabled,
derived completion indicator: non-empty saved answers display checked and blank
answers display unchecked. A frontend regression test covers the answered
state, and the rebuilt package was rechecked in Edge.

![Accepted packaged HIPAA assessment](EDGE_ASSESSMENT_ACCEPTED.png)

## Packaging workflow check

Sequential ARM64 and x64 builds now retain both ZIPs and checksum files even
though the frontend build recreates `dist`. Both retained packages passed the
isolated verifier after the fix.

## Remaining physical acceptance

- Repeat the package run with the host network adapter disabled. This is not
  safe to perform in the active remote development session.
- Observe downloaded-file SmartScreen behavior from the intended distribution
  channel. Local build execution does not create downloaded-file reputation.
- Run the x64 package on native x64 Windows hardware; the current x64 result is
  under Windows-on-ARM emulation.
