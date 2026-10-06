# CMMC SSP template approval record — v1

## Release decision

- **Status:** approved for governed use under delegation.
- **Ticket:** GitHub issue #107.
- **Approver:** Johnathan Dean, by delegation on October 6, 2026. His
  instruction was to decide from the material already supplied. He should
  confirm this record on review.
- **Template version:** `cmmc-ssp-v1`.

## Governed artifact

| Artifact | Path | SHA-256 |
|---|---|---|
| SSP structure | `docs/templates/cmmc/ssp-v1/structure.json` | `f55f0006b8f09a37a94e250a8663a99a3878e7ac328c21af84a3687fe21dab6d` |

`api/ssp.py` refuses to generate if these bytes change. Any change needs a new
template version and a new approval record (#100).

## Provenance and sanitization gate (ADR 0016)

- **Source:** the public NIST SP 800-171 Rev. 2 CUI SSP template, downloaded
  October 6, 2026 from
  `https://csrc.nist.gov/CSRC/media/Publications/sp/800-171/rev-2/final/documents/CUI-SSP-Template-final.docx`.
  SHA-256 `341a8cad3fc26efa567ac304097e0cabd8191925ce743169bb2e9bd1b41341a4`.
- **Nature:** a U.S. Government work. It contains no client material, client
  identifiers, CUI, or original client SSP examples. Nothing client-derived was
  used. The client SSP examples kept outside Git were not consulted.
- **What was taken:** the section structure only:
  1. System Identification
  2. System Environment
  3. Requirements, each with a status and an implementation statement
  4. Record of Changes
- **What was changed:** NIST's *Not Applicable* status choice is removed,
  because CMMC has no N/A (Johnathan, October 6, 2026). The statuses are
  *Implemented* (derived Met) and *Planned to be Implemented* (derived Not Met,
  with POA&M items listed).
- **Not committed:** the NIST DOCX itself. Only the URL and hash are recorded.
- **Verification:**
  - `api/tests/test_issue_107_cmmc_ssp.py` refuses a changed structure file.
  - The CMMC catalog's client-identifier scan covers derived catalog
    artifacts. This structure file holds no free text beyond headings.
