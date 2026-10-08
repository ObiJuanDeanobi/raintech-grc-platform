# Redesign validation against proven tools — October 8, 2026

Second research pass, requested by Johnathan: check the proposed redesign
(`../README.md`, "Proposed shape" and "Product direction") against tools that
are shipping and in use. Three tracks, each with a URL and source label on
every claim:

| Track | File |
|---|---|
| CMMC assessment and deliverables | [cmmc-validation.md](cmmc-validation.md) |
| Compliance as a service, PSA/RMM integrations | [caas-validation.md](caas-validation.md) |
| HIPAA yearly deliverable | [hipaa-validation.md](hipaa-validation.md) |

Verdicts: **VALIDATED** (proven elsewhere), **PARTLY** (proven, with
differences worth copying), **NOVEL** (nobody documents it; a risk to watch),
**CONTRADICTED** (evidence says it is a bad idea).

**Limits.** hhs.gov, dodcio.defense.gov, war.gov, Reddit and G2 refuse this
environment's cloud IP, so OCR guidance and DoD CMMC guides were read through
secondary or archived copies, and there are no Reddit quotes. Primary sources
are being pinned in `docs/sources/` so later checks need no intermediary.
Traction: Vanta, Cynomi and ControlMap are proven at scale; FutureFeed and Totem
are CMMC specialists whose adoption cannot be independently checked.

## Bottom line

Nothing in the redesign is contradicted by shipping tools, with one exception
about V2 integrations (below). The main adjustments are about honesty of the
score, missing scoping records, and keeping imported data out of
determinations.

## CMMC

| Element | Verdict | Adjustment |
|---|---|---|
| Requirement workspace, objectives as rows, derived result | VALIDATED | Totem, Secureframe, ControlMap. |
| Provisional MET, verified + projected scores | PARTLY | Provisional state is proven (Totem "Trending Met", Kaseya Rapid Baseline). Two scores are NOVEL. **Verified score is the headline; projected is secondary.** Inflated self-scores are a False Claims Act exposure: MORSECORP settled for $4.6M in March 2025 after posting 104 when a third-party analysis found −142 ([DOJ](https://www.justice.gov/opa/pr/defense-contractor-morsecorp-inc-agrees-pay-46-million-settle-cybersecurity-fraud)). |
| Live SPRS with arithmetic | VALIDATED | Show literal arithmetic ("110 − 5 − 3 …"). |
| Inline 32 CFR 170.21 checks | PARTLY | Only one vendor claims it. Keep. |
| NOT MET → POA&M | PARTLY | One click, user-initiated, plus a "NOT MET not on any POA&M" count. Not automatic. |
| Implementation statement → SSP | VALIDATED | Allow optional per-objective statements. |
| Evidence library, staleness | VALIDATED | **Expired evidence turns verified MET back to evidence pending** (Drata pattern). |
| Drafts any time, gap package, one issue step | PARTLY | Proven. DRAFT watermark and checklist are new; checklist warns, never blocks. |
| Interview mode | PARTLY | By family proven (Kaseya). By role and keyboard shortcuts NOVEL. |
| Yearly carry-forward | VALIDATED | ControlMap Snapshots, Kaseya. |

**Missing from the redesign:**
- **High:** asset inventory with CMMC asset categories and a CUI inventory
  (32 CFR 170.19 expects them in the SSP); inheritance from external service
  provider responsibility matrices.
- **Medium:** SPRS submission sheet; policy templates; expected-evidence
  checklist; partial credit for 3.5.3 and 3.13.11.
- **Open ground:** affirmation tracking (32 CFR 170.22). No vendor documents it.

## Compliance as a service

| Feature | Verdict | Note |
|---|---|---|
| Home queue across clients | VALIDATED; "waiting on client" lane PARTLY | Everyone has a cross-client view, as status boards. |
| 12-month service-year strip | NOVEL view, PARTLY mechanics | Recurring tasks and yearly roadmaps exist; the strip does not. |
| Monthly meeting → tracked items → client summary | PARTLY | Proven in vCIO/QBR tools (ScalePad Lifecycle Manager), not in GRC tools. |
| Regulatory change log with affected clients | NOVEL | Vendors only update content and publish release notes. Differentiator. |
| Yearly carry-forward | VALIDATED | |
| Recurring reviews, staleness | VALIDATED | |
| V2 Halo PSA / NinjaOne pre-fill | PARTLY; **pre-filling answers CONTRADICTED** | Profile and inventory pre-fill are common. No tool turns RMM data into assessment answers; it becomes evidence or pass/fail checks for a human determination. |

**Integration facts:** both APIs are REST with OAuth2 and usable from a local
desktop app. HaloPSA exposes clients, sites, users, assets, installed software
and tickets; NinjaOne exposes devices, software inventory, patch and antivirus
status, users and contacts. NinjaOne's client-credentials flow needs testing on
a real tenant.

**Needs a decision before V2:** pulling client RMM/PSA data and credentials onto
Johnathan's machine may bring the tool and RainTech into a client's CMMC
assessment scope as an external service provider handling security protection
data. Write an ADR before any integration work.

**Missing:** push work out as Halo tickets; per-control responsibility (who
does what); client templates; policy acknowledgement tracking; scheduled
reports; review-and-publish with history for imported data; cost on POA&M
lines; a frozen yearly snapshot.

## HIPAA

| Element | Verdict | Note |
|---|---|---|
| Two-sheet POA&M (cited gaps vs enhancements) | VALIDATED | Matches HHS's voluntary Essential/Enhanced goals; small-practice vendors rarely separate them. |
| POA&M columns | VALIDATED | Match the federal POA&M fields (OMB M-02-01). |
| SRA scope gate, yearly carry-forward | VALIDATED | |
| No "annual requirement" wording | VALIDATED | Competitors get this wrong (HIPAA One), as does the current template. The Security Rule says periodic. The only annual obligation found is CMS MIPS, for clients in that program. |
| Status list | PARTLY | Add **Risk Accepted** and **Verified**. |
| Risk shown to client | PARTLY | Publish a mapping from the internal 5×5 model to client levels. |
| "Changes since last year" section | NOVEL | NIST SP 800-30r1 Appendix K expects a repeat assessment to cite the prior one. |
| RainTech template Appendix D risk method | **CONTRADICTED** | Sums five factors (double-counts gaps); facility-crime likelihood scale and $1M+ impact scale; no per-asset threat/vulnerability register, which OCR treats as the difference between a gap analysis and a risk analysis. The November 2025 client version already drops Appendix D. Keep the 10/8/5/2/0 impact values; they are NIST's. |

**Template approach (Johnathan's rule: keep the template unless there is a good
reason).** Generate the November 2025 client template as it is. Fix the errors
recorded in `../hipaa-report-reference.md`. Add, without restructuring:
1. Business associate / BAA inventory
2. Training, incident and contingency-test summaries
3. Per-asset risk register from the SRA (fills the gap above)
4. Changes since last year
5. Optional recognized security practices section (Public Law 116-321,
   confirmed signed January 5, 2021); no safe-harbor claim

`hipaa-validation.md` section 10 has a fuller 15-section restructure. It is
recorded as an option, not the recommendation, because of the template rule.

One item for Johnathan's call: the executive summary's "% compliant" figures.
ADR 0011 bars presenting a generic compliance percentage as an assessment
conclusion. Counts by status (implemented / partial / not / N/A) say the same
thing without that problem.
