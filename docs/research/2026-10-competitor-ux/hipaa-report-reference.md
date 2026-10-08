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

## Client version (November 2025) and how it differs

A client report from November 2025, read the same way (structure only), is the
newer, client-facing form of the same template. Differences from the RainTech
internal version above:

- **Annual Review Certification** page after the executive summary: assessor
  certifies the assessment was done under 164.308(a)(1)(ii)(A), with signature.
- **Executive summary, compliance table** by rule (Security Rule, Breach
  Notification Rule, Privacy Rule) with Fully / Partially / Non-Compliant /
  Total / % columns, instead of by safeguard domain with an N/A column.
- **Executive summary, risk table** counting POA&M findings by risk level
  (High / Moderate / Low) and by sheet (HIPAA Controls, Control Enhancements,
  Site Controls), instead of the five-factor organizational risk score.
- **Appendix B is "Control Implementation Statements"** (about 140 pages): for
  every citation (Security Rule standards, Breach Notification and Privacy Rule
  paragraphs), the client's implementation narrative with policy references,
  Domain, Level, Score and Yes/No. In effect a HIPAA system security plan.
- **No Appendix D** (organizational risk calculation).
- Privacy Rule in scope (covered entity), so about 135 citations in total.

## Template principle (Johnathan, October 8, 2026)

Keep the overall template. Change it only where there is a good reason, such as
an accuracy or consistency problem below. The tool generates this report; it
does not redesign it.

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

Items 1, 4 and the risk-method point below also appear in the November 2025
client version. That version adds these consistency problems, which a generator
working from one set of records would prevent:

- **Appendix B and the POA&M disagree.** Facility Access Controls
  (164.310(a)(1)) is scored 1 / 1, "Yes", and its narrative says the client
  "partially complies" with no contingency plan for facility operations; the
  POA&M carries a High finding against 164.310(a)(2)(i) for the same gap.
- **Executive summary and Appendix B disagree.** The summary shows Security
  Rule 18 compliant, 0 partial, 4 non-compliant of 22. Appendix B scores only
  one standard 0 / 1 (Contingency Plan, 164.308(a)(7)) and one N/A (Group
  Health Plans, 0 / 0). The four POA&M items are implementation specifications
  under two standards, so they are counted at a different level than the table.
  "Partially compliant" is never used even where the narrative says partial.
- **N/A counted as compliant.** Three Privacy Rule rows are scored 0 / 0, Not
  Applicable, yet the summary shows Privacy Rule 94 of 94 fully compliant.
- **Findings without a home.** The risk table counts 4 Site Controls findings;
  the POA&M workbook shared with it has no Site Controls sheet.
- **Numbering.** Section 3.0's subsections are numbered 4.1–4.3, then 4.0
  follows.
- **Citation format.** "164.308(a)(1)(II)(A)" should be (ii)(A).

Earlier findings from the RainTech internal version:

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
