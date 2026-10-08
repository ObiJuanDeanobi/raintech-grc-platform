# Pinned primary sources

This directory holds pinned copies of the primary regulatory and guidance texts that
RainTech GRC research relies on. Any agent or reviewer can check a claim against the
official text offline, without relying on law-firm or vendor summaries.

Every file here is a work of the U.S. Government (statute, regulation, Federal Register
document, agency guidance, or NIST publication) and is not subject to copyright in the
United States (17 U.S.C. 105).

## Rules for using and extending this library

- Cite the pinned file and its section, page, or paragraph. Do not cite a secondary
  summary when a primary text is pinned here.
- Each file was obtained from the official issuing host. Where that host blocked this
  environment, the file is a `web.archive.org` capture of the **official URL**, and the
  manifest records the capture timestamp. No third-party re-hosts (vendor, law firm,
  aggregator) are used.
- eCFR XML comes from the eCFR versioner API
  (`https://www.ecfr.gov/api/versioner/v1/full/{date}/title-{n}.xml?...`) at the point-in-time
  date shown in the filename. 2026-10-06 was eCFR's "up to date as of" date for Titles 32
  and 48 when these files were retrieved.
- Verify integrity with `sha256sum -c` against the hashes below. When you add or refresh a
  file, add a row and keep the superseded file unless it is clearly wrong. Where a source
  has changed since it was pinned, the older version is evidence of what applied at the time.
- Skip anything over 25 MB and record it under "Not obtained".

All files were retrieved on **2026-10-08**. Each one was checked after download: PDFs open
in `pdfinfo` with the expected title and first page, XML parses with `xmllint`, and HTML
carries the expected `<title>`.

Total size of `docs/sources/`: **40,740,531 bytes (about 38.9 MiB)** across the 34 pinned files, not counting this README
(cmmc-dfars 21.0 MB, hipaa 19.7 MB). The largest files are the CMMC program final rule PDF
(11.5 MB) and HICP (13.8 MB).

## Important context captured by these sources (as of 2026-10-08)

- **CMMC Phase 2 is suspended.** On July 13, 2026, the Department of War (formerly DoD)
  suspended the November 10, 2026 Phase 2 transition. The DoW CIO page and the
  implementing memo say Phase 1 self-assessment requirements remain in place and DFARS
  252.204-7012 remains in effect. They also say requiring activities may designate only
  CMMC Level 1 (Self) or Level 2 (Self) during the suspension. See `DoW-CIO-memo-…`,
  `DoW-memo-…`, the war.gov release, and `dowcio-CMMC-home.html`. As of the retrieval date,
  the Federal Register API search found no FR notice about the suspension. 32 CFR 170 and the
  DFARS text in eCFR are unchanged by it.
- **The DoD CIO site moved to `dowcio.war.gov`.** `dodcio.defense.gov` returns Akamai 403 to
  this environment, but `dowcio.war.gov` served pages and PDFs directly. The CMMC Hashing
  Guide is no longer linked from the current Resources page, and its old URL now returns
  404, so it was pinned from an archive capture.
- **HIPAA Security Rule NPRM (RIN 0945-AA22).** The Unified Agenda entry under reginfo pubId
  202510 (labelled "2026") moves the rule to **Long-Term Actions**, with Final Action
  "07/00/2027". The Spring 2025 entry listed it at Final Rule Stage with Final Action
  "05/00/2026". Both are pinned. The NPRM is not a final rule.

## Manifest: `cmmc-dfars/`

| File | Title | Issuing body | Version / date | Original URL | How obtained | SHA-256 | Size (bytes) |
|---|---|---|---|---|---|---|---|
| `cmmc-dfars/title-32-part-170-2026-10-06.xml` | 32 CFR Part 170, Cybersecurity Maturity Model Certification (CMMC) Program (whole part) | DoD (eCFR, OFR/GPO) | eCFR point-in-time 2026-10-06 (latest amendment 2024-12-16) | https://www.ecfr.gov/api/versioner/v1/full/2026-10-06/title-32.xml?part=170 | Official API | `3dc8b9bebbe56753206429657cbac24ff32bfd64c75356ba276af38a1032b628` | 178061 |
| `cmmc-dfars/title-48-part-204-subpart-204.73-2026-10-06.xml` | DFARS Subpart 204.73, Safeguarding Covered Defense Information and Cyber Incident Reporting | DoD (eCFR) | 2026-10-06 | https://www.ecfr.gov/api/versioner/v1/full/2026-10-06/title-48.xml?part=204&subpart=204.73 | Official API | `a881401f5124c64dc88d311198f047a87d1036a9f58e6524591763babb3ff293` | 13451 |
| `cmmc-dfars/title-48-part-204-subpart-204.75-2026-10-06.xml` | DFARS Subpart 204.75, Cybersecurity Maturity Model Certification | DoD (eCFR) | 2026-10-06 | https://www.ecfr.gov/api/versioner/v1/full/2026-10-06/title-48.xml?part=204&subpart=204.75 | Official API | `e9734077b5b48659c1e4205949da9734ed2f1bb2d1ed2087252711bea91aab21` | 11148 |
| `cmmc-dfars/title-48-part-204-subpart-204.76-2026-10-06.xml` | DFARS Subpart 204.76, Supplier Performance Risk System (204.7600-7604; SPRS risk assessments used in evaluating offers. NIST SP 800-171 DoD Assessment procedures are in Subpart 204.73, not here) | DoD (eCFR) | 2026-10-06 | https://www.ecfr.gov/api/versioner/v1/full/2026-10-06/title-48.xml?part=204&subpart=204.76 | Official API | `8b57b99a65ae5adf1a8bb171220bb57ed49b9fb1c4bcea29279fbcaa04596479` | 6898 |
| `cmmc-dfars/title-48-section-252.204-7012-2026-10-06.xml` | DFARS 252.204-7012, Safeguarding Covered Defense Information and Cyber Incident Reporting | DoD (eCFR) | 2026-10-06 | https://www.ecfr.gov/api/versioner/v1/full/2026-10-06/title-48.xml?part=252&section=252.204-7012 | Official API | `4801cdb4381ed1a10352a3213abf95aacf9a1a96e461081efbb8599a29a428c5` | 17260 |
| `cmmc-dfars/title-48-section-252.204-7019-2026-10-06.xml` | DFARS 252.204-7019, Notice of NIST SP 800-171 DoD Assessment Requirements | DoD (eCFR) | 2026-10-06 | https://www.ecfr.gov/api/versioner/v1/full/2026-10-06/title-48.xml?part=252&section=252.204-7019 | Official API | `7d0007beafd3dc4c4070904c86ef50d9c24086f6fe15cecbe59e6e2a3c3c7cd1` | 8326 |
| `cmmc-dfars/title-48-section-252.204-7020-2026-10-06.xml` | DFARS 252.204-7020, NIST SP 800-171 DoD Assessment Requirements | DoD (eCFR) | 2026-10-06 | https://www.ecfr.gov/api/versioner/v1/full/2026-10-06/title-48.xml?part=252&section=252.204-7020 | Official API | `167121244facf610a59215e5e98d69c3462a8b5425bffcea83946086b7846c23` | 11376 |
| `cmmc-dfars/title-48-section-252.204-7021-2026-10-06.xml` | DFARS 252.204-7021, Contractor Compliance With the CMMC Level Requirements | DoD (eCFR) | 2026-10-06 | https://www.ecfr.gov/api/versioner/v1/full/2026-10-06/title-48.xml?part=252&section=252.204-7021 | Official API | `12e3e97e0b68ef94283ee364251a78c71dc82894af6c4007a9a8a880c1122499` | 9017 |
| `cmmc-dfars/title-48-section-252.204-7025-2026-10-06.xml` | DFARS 252.204-7025, Notice of CMMC Level Requirements (added for completeness) | DoD (eCFR) | 2026-10-06 | https://www.ecfr.gov/api/versioner/v1/full/2026-10-06/title-48.xml?part=252&section=252.204-7025 | Official API | `bae92457ee8b06ce27725624c88cf0029b9032655f9ffd636587eccd189842ef` | 3164 |
| `cmmc-dfars/FR-2024-22905-89FR83092-CMMC-program-final-rule.pdf` | Cybersecurity Maturity Model Certification (CMMC) Program, final rule (RIN 0790-AL49), 146 pp. | DoD, Federal Register | 89 FR 83092, 2024-10-15 (FR Doc. 2024-22905) | https://www.govinfo.gov/content/pkg/FR-2024-10-15/pdf/2024-22905.pdf | Direct (found via Federal Register API) | `34105216b8735f14d42261d2a6794d6f12dacc4fa60bfc30cb2589d1a7dc5fc3` | 11455373 |
| `cmmc-dfars/FR-2025-17359-90FR43560-DFARS-CMMC-final-rule.pdf` | DFARS: Assessing Contractor Implementation of Cybersecurity Requirements (DFARS Case 2019-D041), final rule (RIN 0750-AK81) | DoD/DARS, Federal Register | 90 FR 43560, 2025-09-10 (FR Doc. 2025-17359) | https://www.govinfo.gov/content/pkg/FR-2025-09-10/pdf/2025-17359.pdf | Direct (found via Federal Register API) | `9df5860513d47b08b6e189681c92652d0d58aeedd7ab131c288c65bdb8f0589e` | 409306 |
| `cmmc-dfars/NIST.SP.800-171r2.pdf` | NIST SP 800-171 Rev. 2, Protecting Controlled Unclassified Information in Nonfederal Systems and Organizations | NIST | Rev. 2, Feb 2020 (incl. Jan 2021 updates) | https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-171r2.pdf | Direct | `298bdbfcf6a4890a564b225c893230a0b32b2e69e3b98dd898aaeb1d544c5e12` | 1539170 |
| `cmmc-dfars/NIST.SP.800-171A.pdf` | NIST SP 800-171A, Assessing Security Requirements for Controlled Unclassified Information | NIST | June 2018 | https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-171A.pdf | Direct | `21bf3acc43f4284f723639b82eb71e3ce597fa3610f7e9dcf5e8484e22bc0f71` | 1233537 |
| `cmmc-dfars/CMMC-Assessment-Guide-Level-2-v2.pdf` | CMMC Assessment Guide, Level 2 | DoD CIO (now DoW CIO) | Version 2.13, Sept 2024 (DoD-CIO-00003) | https://dowcio.war.gov/Portals/0/Documents/CMMC/AssessmentGuideL2v2.pdf | Direct (current DoW CIO host) | `0dcaba1626a0d23893981d74dd3f0f2338fff54cece67d81bc811ce76392d867` | 2272014 |
| `cmmc-dfars/CMMC-Scoping-Guide-Level-2-v2.pdf` | CMMC Scoping Guide, Level 2 | DoD CIO (now DoW CIO) | Version 2.13, Sept 2024 (DoD-CIO-00006) | https://dowcio.war.gov/Portals/0/Documents/CMMC/ScopingGuideL2v2.pdf | Direct (current DoW CIO host) | `377b758393908d6c20a9813fa213c5d3ec36e00018a798d09e59f00eb8627981` | 699925 |
| `cmmc-dfars/CMMC-Hashing-Guide-v2.14.pdf` | CMMC Hashing Guide (CMMC Artifact Hashing Tool User Guide) | DoD CIO | Version 2.14, Sept 2025 (cleared Sep 12, 2025) | https://dowcio.war.gov/Portals/0/Documents/CMMC/HashingGuide_v2.14.pdf (earlier at dodcio.defense.gov/Portals/0/Documents/CMMC/HashingGuide_v2.14.pdf) | web.archive.org snapshot 20260410162327 of the official URL (live URL now returns 404; not linked from current Resources page) | `339c1a085e705fc3bf77d7f3864c4865b7cf8c89e9572a15ffca7bad27ebe1a9` | 926602 |
| `cmmc-dfars/DoD-NIST-SP-800-171-Assessment-Methodology-v1.2.1.pdf` | NIST SP 800-171 DoD Assessment Methodology | DoD, OUSD(A&S) DPC | Version 1.2.1, June 24, 2020 | https://www.acq.osd.mil/asda/dpc/cp/cyber/docs/safeguarding/NIST-SP-800-171-Assessment-Methodology-Version-1.2.1-6.24.2020.pdf | web.archive.org snapshot 20261006090508 of the official URL (the official host's TLS chain failed verification here) | `dd88416ca43f34e817c05b9cb416ffce47f615765a9fd0e1cdc52b9f2de60835` | 374501 |
| `cmmc-dfars/CMMC-FAQs-v6.pdf` | CMMC Program Frequently Asked Questions | DoW CIO | July 2026 (v6, post-suspension) | https://dowcio.war.gov/Portals/0/Documents/CMMC/FAQsv6.pdf | Direct | `b2563aabbfd3ad4013e2ade962641813cf9ff6976c07a446864a2b4f7ed44394` | 446494 |
| `cmmc-dfars/DoW-CIO-memo-Implementing-Suspension-CMMC-Phase-II.pdf` | Implementing Suspension of CMMC Phase II (memo with Attachment 1, "Cybersecurity Maturity Model Certification Procedures") | DoW CIO | July 13, 2026 (cleared 26-P-1023) | https://dowcio.war.gov/Portals/0/Documents/Library/ImplementingSuspensionCMMC-PhaseII.pdf | Direct | `e5a0fdc30466b8453f345bc8f8ab14f6ae8ca39f806a441646bb06416bbc41e0` | 753846 |
| `cmmc-dfars/DoW-memo-Removing-Barriers-to-DIB-Expansion-CMMC-Reform.pdf` | Removing Barriers to DIB Expansion (CMMC reform memo; signature page is an image with no text layer) | Department of War | July 13, 2026 (cleared 26-P-1023) | https://dowcio.war.gov/Portals/0/Documents/Library/CMMC-ReformMemo.pdf | Direct | `71325d64ddd1181a54cb511c8d07d74f03e5265846983a02b3785f685c30a185` | 443630 |
| `cmmc-dfars/war-gov-release-4542329-suspends-CMMC-Phase-II-web-20260825123422.html` | Forging the Arsenal of Freedom: Department of War Suspends CMMC Phase II Requirements (press release) | Department of War | July 13, 2026 | https://www.war.gov/News/Releases/Release/Article/4542329/forging-the-arsenal-of-freedom-department-of-war-suspends-cmmc-phase-ii-require/ | web.archive.org snapshot 20260825123422 (war.gov returns 403 here) | `df68be67e50ee9815416f557dfb742428f8403c160a2fdccfbd0a5eddc6ea86b` | 119932 |
| `cmmc-dfars/dowcio-CMMC-home.html` | CIO - Cybersecurity Maturity Model Certification (program home page with the suspension notice and memo links) | DoW CIO | As served 2026-10-08 | https://dowcio.war.gov/CMMC/ | Direct | `1ad773f71f439df05bab953e576a0bea140dbfefa2d4351733e2757eb429ef8e` | 40936 |
| `cmmc-dfars/dowcio-CMMC-Resources-Documentation.html` | CIO - CMMC Resources & Documentation (official document index) | DoW CIO | As served 2026-10-08 | https://dowcio.war.gov/CMMC/Resources-Documentation/ | Direct | `aae4731522ccdbd08a4e02a56cd3d32a04a25b6d5c086d9fe20094c537a46ac1` | 42280 |

## Manifest: `hipaa/`

| File | Title | Issuing body | Version / date | Original URL | How obtained | SHA-256 | Size (bytes) |
|---|---|---|---|---|---|---|---|
| `hipaa/FR-2024-30983-90FR898-HIPAA-Security-Rule-NPRM.pdf` | HIPAA Security Rule To Strengthen the Cybersecurity of Electronic Protected Health Information, NPRM (RIN 0945-AA22) | HHS OCR, Federal Register | 90 FR 898, 2025-01-06 (FR Doc. 2024-30983) | https://www.govinfo.gov/content/pkg/FR-2025-01-06/pdf/2024-30983.pdf | Direct (found via Federal Register API) | `d5e1ec4107308e5ef2f261a77b1c6f8709910380618381677edea9e0a40075f7` | 1067294 |
| `hipaa/reginfo-RIN-0945-AA22-unified-agenda-2026-pubId-202510.html` | Unified Agenda entry, RIN 0945-AA22 (agenda labelled "2026"; Long-Term Actions; Final Action 07/00/2027) | OMB OIRA / HHS OCR | pubId 202510 (latest listed) | https://www.reginfo.gov/public/do/eAgendaViewRule?pubId=202510&RIN=0945-AA22 | Direct | `add6e1e9a5612b9be953a66c84d7414d02f318e8d67fb5e1650cdcd5cbf6b93c` | 55591 |
| `hipaa/reginfo-RIN-0945-AA22-unified-agenda-2026-pubId-202510.xml` | Same entry, reginfo XML export | OMB OIRA / HHS OCR | pubId 202510 (RUN_DATE 2026-10-08) | https://www.reginfo.gov/public/do/eAgendaViewRule?pubId=202510&RIN=0945-AA22&operation=OPERATION_EXPORT_XML | Direct | `bda99c1c11d3a054d4da5fc3dcd8f8cc3bdab46973a0a9e89ad5858551e92e42` | 4581 |
| `hipaa/reginfo-RIN-0945-AA22-unified-agenda-spring-2025-pubId-202504.html` | Unified Agenda entry, RIN 0945-AA22 (Spring 2025; Final Rule Stage; Final Action 05/00/2026), kept for history | OMB OIRA / HHS OCR | pubId 202504 | https://www.reginfo.gov/public/do/eAgendaViewRule?pubId=202504&RIN=0945-AA22 | Direct | `191755bfa76c6f358364b4e5790aa7a74181d4ad567aec9b2490fe199e98b3bd` | 55581 |
| `hipaa/HHS-OCR-Guidance-on-Risk-Analysis-web-20261001150845.html` | Guidance on Risk Analysis (HHS.gov page) | HHS OCR | Page "Content last reviewed August 12, 2026" | https://www.hhs.gov/hipaa/for-professionals/security/guidance/guidance-risk-analysis/index.html | web.archive.org snapshot 20261001150845 (hhs.gov returns 403 here) | `3dce2de7f4e7c475694925b53385c92ed54bf992027ed71cb2d76a94898a25a5` | 225226 |
| `hipaa/HHS-OCR-Guidance-on-Risk-Analysis-rafinalguidancepdf.pdf` | Guidance on Risk Analysis Requirements under the HIPAA Security Rule (PDF, 9 pp.) | HHS OCR | Original guidance issued July 14, 2010 | https://www.hhs.gov/sites/default/files/ocr/privacy/hipaa/administrative/securityrule/rafinalguidancepdf.pdf | web.archive.org snapshot 20260512023051 (hhs.gov returns 403 here) | `95a54f2d29fce484e198e16edd7fe8e45cab03b723aa33c1fcbbee6082dfb121` | 37040 |
| `hipaa/HHS-OCR-HIPAA-Audit-Protocol-web-20260710234404.html` | Audit Protocol – Updated July 2018 (HHS.gov page) | HHS OCR | Protocol updated July 2018; page "Content last reviewed February 3, 2025" | https://www.hhs.gov/hipaa/for-professionals/compliance-enforcement/audit/protocol/index.html | web.archive.org snapshot 20260710234404 (latest capture found; hhs.gov returns 403 here) | `7aef4c7d2673b80d587d3fa9afc2a7d621b8147544b38fbdb5729e9d994ac4a2` | 611134 |
| `hipaa/HHS-ONC-SRA-Tool-User-Guide-v3.7.pdf` | Security Risk Assessment Tool v3.7 User Guide | HHS ASTP/ONC with HHS OCR | v3.7 (the guide's text says "Updated: August 7, 2025"; file uploaded Sept 2026) | https://healthit.gov/wp-content/uploads/2026/09/SRA_Tool_User_Guide_Version_3.7.pdf (via https://healthit.gov/sra_tool_user_guide_version_3-7/) | Direct | `80765539705927cf80118e05a9efc36d85f9f881d3e7a430d17412b0b1da7dd3` | 2816723 |
| `hipaa/HHS-405d-HICP-Main-Document.pdf` | Health Industry Cybersecurity Practices: Managing Threats and Protecting Patients (HICP main document) | HHS 405(d) Program / HSCC | 2023 Edition | https://405d.hhs.gov/Documents/HICP-Main-508.pdf | Direct (405d.hhs.gov was reachable) | `3d4a2ebe13b68eb0dc15255f481421917ab3ea0fc20e7b26b66a248df56ff600` | 13821123 |
| `hipaa/PLAW-116publ321.pdf` | Public Law 116-321 (amends HITECH Act to recognize recognized security practices) | U.S. Congress (GPO) | Enacted Jan 5, 2021 | https://www.govinfo.gov/content/pkg/PLAW-116publ321/pdf/PLAW-116publ321.pdf | Direct | `decad9cedef504d156b9e75bf341253adad3966d7b129d223c7f8eabc67f1fe1` | 203094 |
| `hipaa/NIST.SP.800-30r1.pdf` | NIST SP 800-30 Rev. 1, Guide for Conducting Risk Assessments | NIST | Rev. 1, Sept 2012 | https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-30r1.pdf | Direct | `f214087f0bdb35932a28c16eb93932a33c67a6edfb5e6f1638866bd201c98e04` | 826897 |

## Already pinned elsewhere (`catalog/sources/`, not duplicated)

| File | Title | Version / date | SHA-256 | Size (bytes) |
|---|---|---|---|---|
| `catalog/sources/NIST.SP.800-66r2.pdf` | NIST SP 800-66 Rev. 2, Implementing the HIPAA Security Rule | Rev. 2, Feb 2024 | `3910c9b29e06d978bf17258d94e851d8d3d786ceb65beb352cc93271f4d3173e` | 1626188 |
| `catalog/sources/title-32-part-170-section-170.21-2026-10-01.xml` | 32 CFR 170.21, POA&M requirements | eCFR 2026-10-01 | `352282ff13456ca53c9dc97ad49c499d56494681c1f67072d96ea8190698f936` | 3603 |
| `catalog/sources/title-32-part-170-section-170.24-2026-10-01.xml` | 32 CFR 170.24, CMMC Scoring Methodology | eCFR 2026-10-01 | `62475756e7dfeb72c3965d538a88a767a6aea7cc5df59dbfb10a2990d9770e52` | 11870 |
| `catalog/sources/title-45-part-164-subpart-C-2026-07-01.xml` | 45 CFR 164 Subpart C, Security Standards for the Protection of ePHI | eCFR 2026-07-01 | `9041a339ad1eaec5626b6c7fff5bebbc625dd8757eefe009e3e986c3c5e5a6f0` | 37860 |
| `catalog/sources/title-45-part-164-subpart-D-2026-07-01.xml` | 45 CFR 164 Subpart D, Breach Notification | eCFR 2026-07-01 | `3ea6f9e9836e0b7f8a6e300089312460abeeb53c4c20b39f1718b35f34c96949` | 16205 |
| `catalog/sources/title-45-part-164-subpart-E-2026-07-01.xml` | 45 CFR 164 Subpart E, Privacy of Individually Identifiable Health Information | eCFR 2026-07-01 | `68e0a1f098347fbd987f4f6433dd28a3c0986193b044b99906e86403c1c84b29` | 216635 |

The whole-part file `cmmc-dfars/title-32-part-170-2026-10-06.xml` contains 170.21 and 170.24
as well. The section files in `catalog/sources/` are not superseded: Part 170 has not been
amended since 2024-12-16, so both dates give the same text.

## Not obtained

- **Federal Register notice on the July 2026 CMMC Phase 2 suspension.** None exists as of
  2026-10-08. Federal Register API searches for "CMMC" and "Cybersecurity Maturity Model
  Certification" from 2025-10-01 onward, and for RINs 0790-AL49 and 0750-AK81, returned no
  suspension notice. The suspension is documented only by the DoW memos, the release, and
  the DoW CIO pages pinned above.
- **Live hhs.gov and www.war.gov copies.** Both return Akamai 403 to this environment, so
  the HHS OCR pages and the war.gov release are archive captures of the official URLs (see
  the timestamps above).
- **Newer CMMC Hashing Guide.** Only v2.14 (Sept 2025) was found. Its official URL now
  returns 404, and the current DoW CIO Resources page no longer lists a hashing guide.
  Guessed v2.15/v3 URLs on dowcio.war.gov also returned 404. Check for a replacement before
  relying on v2.14.
- No file was skipped for size. The largest pinned file is 13.8 MB.

## Verify

```sh
cd docs/sources
sha256sum cmmc-dfars/* hipaa/*   # compare against the manifest tables
```
