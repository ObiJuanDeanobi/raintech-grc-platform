# HIPAA yearly report reference format (structure only)

Source: RainTech's own "HIPAA Risk Assessment Report" dated 09/22/2025 (v1.0),
read from RainTech SharePoint on October 8, 2026 at Johnathan's request. It is
the template his client reports follow (the client POA&M in
`hipaa-poam-reference.md` matches its POA&M format). **Only structure is
recorded here; no report content is committed.**

## Table of contents

- Cover, confidentiality notice on every page
- **Background Information**: what HIPAA is; Privacy, Security and Breach
  Notification Rules in plain language
- **Executive Summary**
  - Compliance by domain: Implemented / Not Implemented / N/A / Score %, for
    Breach Notification Rule, Privacy Rule, Administrative, Physical and
    Technical Safeguards, Organizational Requirements, Policies and Procedures
    and Documentation Requirements, and a total
  - Aggregate risk: Risk Rating, Risk Score, Overall Compliance (maturity
    label), Criticality, Likelihood, Impact, Compliance %, Gap Score, Gaps Found
- **1.0 Introduction**: applicable laws; applicable standards and guidance
  (NIST SP 800-30r1, 800-39, 800-60, 800-115, 800-128, FIPS 140-2, others);
  purpose; scope — system name and boundary, data types and sensitivity,
  documentation reviewed (list), physical sites
- **2.0 Assessment Methodology** (NIST SP 800-30r1 steps): scope, gather
  information, identify threats, assess current measures, determine risk,
  identify remediation, document gaps
- **3.0 List of Findings**, in up to four POA&M sheets:
  1. HIPAA Compliance Controls (required)
  2. Control Enhancements (optional, from other frameworks)
  3. Technical Vulnerabilities (from vulnerability scans)
  4. Site Controls (from site visits and interviews)
- **4.0 POA&M**: definitions of 20 columns (adds Control ID, Finding
  Description and Affected Targets to the columns in `hipaa-poam-reference.md`)
- **5.0 Impact Determination**: Critical / High / Moderate / Low /
  Informational, each with a qualitative range and a semi-quantitative value
  (10 / 8 / 5 / 2 / 0)
- **Appendix A**: key terminology
- **Appendix B**: HIPAA requirements summary — one row per citation: #, Code,
  Practice, Domain, Level, Score (x / 1), Remarks (where the evidence is, or
  what is missing), Status (Yes / No). Security Rule at standard level plus
  Breach Notification Rule paragraphs
- **Appendix C**: POA&M (separate spreadsheet)
- **Appendix D**: organizational risk calculation — Criticality + Likelihood +
  Impact + Compliance + Gap Score = Risk Score, banded Low / Medium Low /
  Medium / Medium High / High, with definition tables for each factor

## What the tool must produce

The yearly HIPAA deliverable is this report plus the POA&M workbook,
regenerated from assessment data rather than written by hand: the domain table,
Appendix B rows, POA&M sheets and risk figures all come from records the tool
already holds or will hold.

New record types this implies beyond the current spec:
- Control enhancements (recommendations without a citation)
- Technical vulnerabilities (scan findings with affected targets)
- Site controls (site-visit findings per physical site)
- Documentation-reviewed list and physical-site list on the Profile

## Problems in the source to fix in the generated version

Found while reading; these are the kind of errors that become findings when a
client's auditor or OCR reads the report.

1. **Annual claim.** Section 1.3 says "The HIPAA law requires that
   organizations annually assess". The Security Rule says periodic
   (45 CFR 164.308(a)(8), 164.316(b)(2)(iii)); ADR 0011 bars this wording.
2. **Percentages do not reconcile with the counts.** Administrative Safeguards
   7 implemented / 2 not = 77.8%, shown 72%; Breach Notification 10 / 7 =
   58.8%, shown 57%; total 31 / 10 = 75.6%, shown 77%. Generated tables must
   compute from the same rows they show.
3. **Stale dates.** Some pages carry 08/19/2024 headers inside the 09/22/2025
   report.
4. **Terminology.** "electronic Private Heath Information"; ePHI is electronic
   protected health information.
5. **Risk method mismatch.** Section 2.5 says risk is the average of
   likelihood and impact; Appendix D sums five factors. Appendix D's likelihood
   scale is about crime, terrorism and natural disaster near a facility, and its
   impact scale starts at $1 million — a facility-risk scale, not one sized for
   small-practice ePHI. There is no per-asset threat and vulnerability register,
   which OCR guidance on risk analysis expects. The tool's SRA (vulnerabilities
   that apply → rated threats on a 5×5 model) should feed this section, with
   the published method matching the method actually used.
