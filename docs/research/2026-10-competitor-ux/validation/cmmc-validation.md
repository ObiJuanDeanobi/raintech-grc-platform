# CMMC redesign validation against shipping tools (second pass)

Date: 2026-10-08. Scope: check each element of the proposed CMMC redesign
(`docs/research/2026-10-competitor-ux/README.md` "Proposed shape" and "Product
direction") against tools that ship today. This pass builds on `cmmc-tools.md` and
`msp-grc.md` and does not repeat them. A citation of the form "(cmmc-tools §1.1)"
points to a claim that was already sourced there.

**Source labels:** [DOCS] = vendor help centre or release notes. [MKT] = vendor
marketing, press release or vendor blog. [REVIEW] = user review (G2/Capterra, seen
only through search snippets). [COMMUNITY] = vendor community forum post by a user.
[PRAC] = practitioner or consultant. [LEGAL] = law-firm analysis. [REG] =
regulation. [3P] = third-party aggregator or directory (low reliability).

**Access limits (read first):**
- **Reddit is unavailable.** reddit.com returned 403. The PullPush archive returned
  429 and refused agent access. `site:reddit.com` searches for Totem and FutureFeed
  returned no Reddit pages. **This document contains no r/CMMC quotes.** LinkedIn
  posts and webinar recordings were not searched; none are quoted.
- G2 and Capterra figures come from search snippets and were not opened directly.
- The ControlMap help centre was read in full through its public Zendesk API, so
  those article bodies are verbatim.
- Totem, FutureFeed and Secureframe help pages were fetched directly.
- Cynomi, Compliance Scorecard, Apptega and Exostar have no public CMMC help docs
  that I could find, so evidence for them is marketing only.
- Nobody used a product hands-on.

---

## 0. Which tools count as "proven": traction signals

| Tool | Signal | Source | Reading |
|---|---|---|---|
| **Vanta** | $150M Series D at $4.15B, July 2025. Roughly 12,000 customers is the most-repeated figure; 7,000 appears in an older source. | [3P SVIC](https://siliconvalleyinvestclub.com/ar/2025/07/24/vanta-raises-150-million-at-a-4-15-billion-valuation/), [3P multiples.vc](https://multiples.vc/private-comps/vanta) | Strongest traction overall. CMMC support is thin: an SPRS widget announced 2026-05-15 [DOCS/COMMUNITY](https://community.vanta.com/x/vanta-product-updates/2radoe2j9i2l/track-your-sprs-score-for-cmmc-level-2-with-vantas). |
| **Drata** | About $328M disclosed ($200M Series C, 2022, at a $2B valuation). One source claims $455M including a 2025 round; that is unconfirmed. No customer count found. | [3P GetLatka](https://getlatka.com/companies/drata), [3P Owler](https://www.owler.com/company/drata/funding) | Large company. No CMMC SPRS/SSP documentation found. |
| **Secureframe** | $56M Series B (2022), $79M total by its own count. "Thousands" of customers per a directory; not verified. Has a "Defense" CMMC product with public help articles. | [MKT newsroom](https://secureframe.com/es-es/newsroom/secureframe-raises-56m-to-accelerate-automated-security-and-compliance) | The best-documented CMMC workflow among the big three. |
| **ScalePad ControlMap** | Acquired by ScalePad in March 2023; terms undisclosed; ControlMap had about 14 staff at the time. G2 rating 4.6/5 from 45 reviews. Monthly 2025–2026 release notes on CMMC. | [MKT ScalePad](https://www.scalepad.com/news/scalepad-acquires-controlmap), [3P MSSP Alert](https://www.msspalert.com/news/scalepad-acquires-controlmap), [REVIEW G2 snippet](https://www.g2.com/products/scalepad-controlmap/reviews) | The most review-validated MSP tool here, with active CMMC development (sub-objective audits, eMASS, GCC). |
| **Cynomi** | $37M Series B, April 2025 (Insight Partners); about $60M total. More than 100 service providers in 2024. Capterra 4.8/5 from 9 reviews. | [MKT Cynomi](https://cynomi.com/news/cynomi-raises-37m-series-b), [3P Channel Insider](https://www.channelinsider.com/tech-companies/cynomi-funding-announcement-april-2025/), [3P parsers.vc](https://parsers.vc/news/240418-cynomi--revolutionizing-cybersecurity-for/), [REVIEW Capterra snippet](https://www.capterra.co.uk/software/1043230/cynomi) | Well funded and MSP-adopted, but CMMC depth is marketing only ([MKT](https://cynomi.com/frameworks/nist-sp-800-171/)). |
| **Kaseya Compliance Manager GRC** | Part of Kaseya, a very large MSP vendor; CMMC 2.0 L2 support updated 2025-11-06. Capterra 3.8/5 from 13 reviews, with a 50% recommend rate. G2 Ease of Use 7.8 against a category average of about 8.9 (msp-grc §1.6). | [MKT Kaseya](https://www.kaseya.com/platform/innovations/compliance-manager-grc-cmmc-2-level-2/), [REVIEW Capterra snippet](https://www.capterra.ca/software/194233/compliance-manager) | Wide MSP distribution, weak satisfaction. |
| **FutureFeed** | Claims "over 1,400 clients and 300+ partners". FedRAMP High authorized (vendor claim). Capterra shows 0 reviews. Teramis partnership (2026-06-16). | [MKT futurefeed.co](https://futurefeed.co/), [REVIEW Capterra](https://www.capterra.co.uk/software/1083169/FutureFeed) | The largest CMMC-specific installed base claimed, with no independent reviews. |
| **Totem** | No customer count published; G2 shows 0 reviews. Veteran-owned, founded 2014. MSP "CMMC Expert" tier. | [MKT totem.tech](https://www.totem.tech/cybersecurity-compliance-software/), [3P G2 seller](https://g2.com/sellers/totem-technologies), [3P Manifest](https://themanifest.com/company/totemtech) | The best-documented CMMC workflow, but traction is unverifiable. |
| **Exostar Certification Assistant / ComplyUp** | Exostar claims more than 50,000 suppliers platform-wide, not specific to this product. Acquired ComplyUp 2024-12-17. Capterra 1.5/5 from 4 reviews, platform-wide. | [3P techleap](https://finder.techleap.nl/news/feed/exostar-acquires-robot-morning-complyup), [MKT Exostar](https://www.exostar.com/products/certification-assistant/) (cmmc-tools §1.3) | Has distribution through primes. No public docs. |
| **Apptega** | $37M (2022) plus $15M (2024) from Mainsail. Partner count "almost tripled" in 2 years; no absolute figure. G2 Leader in 2022. | [3P MSSP Alert](https://www.msspalert.com/news/apptega-raises-37-million-further-engages-mssps-for-automated-cybersecurity-compliance), [3P techleap](https://finder.techleap.nl/news/feed/apptega-secures-15m-for-msp-solutions) | No public CMMC SPRS/POA&M docs found. |
| **Compliance Scorecard** | Funding amount unknown (a VC round in 2023 per Caplight). "10K+ customers" appears only on an unverified aggregator. On the Pax8 and ConnectWise marketplaces. | [3P Caplight](https://www.caplight.com/company/compliancescorecard), [3P kscope](https://api-dev.kscope.io/private-data/companies/compliancescorecard-com), [3P ChannelE2E](https://www.channele2e.com/news/compliance-scorecard-joins-pax8-marketplace-to-streamline-compliance-for-msps) | Has a POA&M and risk register (2024 release, [3P HelpNetSecurity](https://www.helpnetsecurity.com/2024/06/10/compliance-scorecard-msps-cybersecurity/)). No SPRS calculator found. |
| **Ignyte** | No funding or customer data found. A C3PAO; its own pages conflict on whether it is a candidate or authorized. | [MKT Ignyte](https://www.ignyteplatform.com/cybersecurity-awards-and-certifications/) | Minor. |

**Practical tiers for this report:**
- **Proven at scale (general GRC):** Vanta, Drata, Secureframe, Kaseya, ControlMap and Cynomi. Of these, only **Secureframe, ControlMap and Kaseya** publish CMMC-specific workflow docs.
- **CMMC-specialist, well documented, traction unverifiable:** Totem and FutureFeed.
- **Weight given:** Where Secureframe, ControlMap, Totem or FutureFeed docs agree, I treat the element as proven.

---

## 1. Element-by-element validation

### E1. Requirement-centred master-detail workspace (objectives as rows, one click each, requirement result derived)

**Who does it, and how:**
- **Totem** [DOCS]:
  - Control Status lists the controls. Each control expands to its "Organization Actions" (800-171A objectives), and status is set per objective.
  - "A control is Met when all its Organization Actions are Met."
  - Source: [Building an SSP](https://support.totem.tech/building-a-system-security-plan-ssp/) (cmmc-tools §1.1).
- **Secureframe Defense** [DOCS]:
  - "The Control Implementation table breaks it down by each control's assessment objectives and each control's score contribution."
  - "Secureframe only credits requirements you have marked Implemented or Not Applicable."
  - The objective table sits inside the SSP control page.
  - Source: [Understanding your SPRS score](https://support.secureframe.com/en/articles/15111372-understanding-your-sprs-score-in-secureframe).
- **ControlMap** [DOCS]:
  - "Assessment by requirement/objective, and sub-objectives."
  - Since June 2026, audits can be worked "at both the sub-objective level and control level", and each sub-objective rolls up to its parent control.
  - Sources: [CMMC Specific Features](https://help.controlmap.io/hc/en-us/articles/29270822904091-CMMC-Specific-Features), [MKT ScalePad update](https://www.scalepad.com/updates/controlmap-adds-sub-objective-level-cmmc-auditing-with-emass-ready-reporting).
- **Vanta** [DOCS/COMMUNITY]:
  - A requirement shows "Met" once all its controls are Implemented or N/A.
  - Source: [Vanta SPRS widget, 2026-05-15](https://community.vanta.com/x/vanta-product-updates/2radoe2j9i2l/track-your-sprs-score-for-cmmc-level-2-with-vantas).
- **Kaseya** has the opposite pattern: a one-item wizard plus a list view (msp-grc §1.1).

**What users say:**
- ControlMap is "centralized and easy to navigate" [REVIEW G2 AI-summary snippet](https://www.g2.com/products/scalepad-controlmap/reviews?qs=pros-and-cons).
- Kaseya draws "not at all intuitive" [REVIEW Capterra snippet](https://www.capterra.com/p/194233/Compliance-Manager/reviews/).
- No user source praises or criticises split-pane layout as such.

**Verdict: VALIDATED.**
- Objective rows under a requirement, with a derived result, are standard in Totem, Secureframe and ControlMap.
- The specific left-list / right-detail split pane is not documented by any vendor. It is a layout choice, not a model change, so the risk is low.
- **Copy:** Secureframe's per-requirement "score contribution" column on the list, and Totem's expandable rows as a fallback at narrow (Surface portrait) widths.

### E2. Provisional status (MET without evidence = "evidence pending") and two scores (verified vs projected)

**Who does it, and how:**
- **Totem "Trending Met"** [DOCS]:
  - The Questionnaire marks objectives Trending Met.
  - On scoring: "they do not result in any points lost when a control is marked one of these."
  - So Totem's single score is effectively our *projected* score.
  - Sources: [Reviewing your self-assessment score](https://support.totem.tech/reviewing-your-self-assessment-score/), [Using the Questionnaire](https://support.totem.tech/using-the-questionnaire/).
- **ControlMap** [DOCS]:
  - Assessment answers and evidence are separate tracks.
  - The Client Dashboard health score scores "Framework Objectives by status: Compliant = 1 … Partial / Review = 0.5" separately from "Assessment by answer".
  - SPRS itself is calculated from answers only.
  - Source: [Client Dashboard](https://help.controlmap.io/hc/en-us/articles/35547294075803-Client-Dashboard).
- **Vanta and Secureframe** credit status alone ("marked Implemented"). No evidence condition is documented for the score (links above).
- **Kaseya Rapid Baseline** is a fast, explicitly provisional pass that is imported into the formal assessment (msp-grc §1.1).
- **No tool found shows two SPRS numbers.** No tool computes a score that only counts evidenced MET.

**Why the second score is still defensible:**
- In MORSECORP's $4.6M False Claims Act settlement (March 2025), the company had posted 104 to SPRS, while a third-party gap analysis put it at −142. It was the first FCA settlement over failing to update an SPRS score. [LEGAL Skadden](https://www.skadden.com/insights/publications/2025/04/government-contractor-settles-fca-case), [LEGAL Crowell](https://www.crowell.com/en/insights/client-alerts/for-better-or-morse-another-settlement-under-dojs-civil-cyber-fraud-initiative)
- "Your SPRS score is not a form. It is a legal representation to the federal government" [PRAC Elevate](https://elevateconsult.com/resources/videos/sprs-scoring-poams-and-the-false-claims-act-explained/).
- A tool that silently scores unverified MET as met (as Totem's Trending Met does) is exactly how an inflated score gets submitted.

**Risk:**
- Two numbers can confuse.
  - An Apptega customer asked why there were "3 representations of a 22% metric" (README "Orientation").
  - ControlMap needed a help article because users thought its single SPRS breakdown was wrong ([DOCS](https://help.controlmap.io/hc/en-us/articles/52340739755803-SPRS-score-appears-incorrect)).

**Verdict: PARTLY.**
- The provisional state is proven (Totem, Kaseya).
- The dual score is **NOVEL**. Its regulatory and legal rationale is strong, but its UX risk is real.
- **Copy and adjust:**
  - Make *verified* the headline number, labelled "SPRS (submittable)".
  - Show projected as a secondary "if pending evidence lands: 97".
  - Never show two numbers of equal weight.
  - Copy Totem's naming idea: a distinct status word ("Trending Met") rather than a badge on MET.
  - Avoid Totem's bulk Questionnaire that overwrites existing status.

### E3. Live SPRS with arithmetic, plus inline 32 CFR 170.21 Conditional checks

**Who does it, and how:**
- **Live score** is universal:
  - Totem: top of Control Status and the Dashboard.
  - FutureFeed (cmmc-tools §1.2).
  - Secureframe: right side of the SSP dashboard.
  - ControlMap: framework card.
  - Vanta: framework page.
  - Exostar: "in real time as you complete each … requirement" [MKT](https://www.exostar.com/products/certification-assistant/).
- **Arithmetic:**
  - ControlMap's side panel gives a per-objective breakdown, but it displays "+1" for answered objectives that actually count 0. That caused a support article: "If you copy these values into a spreadsheet and sum them, the total won't match" ([DOCS](https://help.controlmap.io/hc/en-us/articles/52340739755803-SPRS-score-appears-incorrect)). This is an anti-pattern to avoid: show 110 minus the deductions, literally.
  - Secureframe shows per-control "score contribution" ([DOCS](https://support.secureframe.com/en/articles/15111372-understanding-your-sprs-score-in-secureframe)).
- **Partial credit for 3.5.3 and 3.13.11:**
  - Totem opens a modal when either is marked Not Met ([DOCS](https://support.totem.tech/reviewing-your-self-assessment-score/)).
  - FutureFeed applies the 3-point partials (cmmc-tools §1.2).
  - Secureframe gives "partial points … only for MFA and FIPS encryption" ([DOCS](https://support.secureframe.com/en/articles/15111372-understanding-your-sprs-score-in-secureframe)).
- **170.21 Conditional checks:**
  - **Secureframe** [MKT]: shows the live score "against the Conditional and Final Level 2 (Self) scoring thresholds" and "flags requirements that can't be deferred to a POA&M" ([secureframe.com/sprs-scoring](https://secureframe.com/sprs-scoring)). Its help article does not describe the flags, so the UI is unverified.
  - **Totem** documents the 88/110 floor and the 1-point rule in its help text, but no inline check is documented ([DOCS](https://support.totem.tech/reviewing-your-self-assessment-score/)).
  - **ControlMap** explicitly leaves eligibility to the customer: "customers remain responsible for determining whether a POA&M is permitted" ([DOCS](https://help.controlmap.io/hc/en-us/articles/29270822904091-CMMC-Specific-Features)).
  - Paid Excel trackers advertise per-control POA&M-eligibility flags and an 88 calculator ([search summary; product page not opened](https://payhip.com/b/HTzXf)). That shows practitioner demand.
- **Caution on secondary sources:** they misstate the rule. One says 1- and 3-point controls can go on a POA&M; another says 70–109 passes ([PRAC petronellatech](https://petronellatech.com/blog/sprs-score-complete-guide-defense-contractors-2026/), [PRAC Modus](https://www.modusadvanced.com/resources/blog/cmmc-sprs-score-navigating-the-cybersecurity-maturity-model)). The primary text is [32 CFR 170.21](https://www.law.cornell.edu/cfr/text/32/170.21). Encoding the rule correctly is a differentiator.

**Verdict:**
- Live score: **VALIDATED**.
- Arithmetic: **VALIDATED**, with a clear lesson from ControlMap.
- Inline 170.21 checks: **PARTLY**. Only Secureframe claims them, in marketing; Totem and ControlMap push them to the user.
- **Copy:**
  - Totem's partial-credit modal.
  - Secureframe's "can't be deferred" flag.
  - Show literal "110 − 5 − 3 − 1 … = 101" arithmetic.

### E4. NOT MET creates a POA&M draft in place

**Who does it, and how:**
- **Secureframe** [DOCS]:
  - Create from the SSP Control Implementation page; "the Issue field pre-fills from the assessment objective".
  - The default status is **Draft**.
  - Setting it to In Progress "automatically set[s] 180 days out".
  - Overdue items show red.
  - Notably: "POA&M items are created by you … so you decide what is formally documented as a gap."
  - Source: [Creating and managing POA&Ms](https://support.secureframe.com/en/articles/15111383-creating-and-managing-poa-ms-plans-of-action-and-milestones).
- **Totem** [DOCS]: multi-select Not Met → "Add to POA&M". CAPs are **not auto-created**, but Totem advises every Not Met appear on a CAP ([Building a POA&M](https://support.totem.tech/building-a-poam/)).
- **ControlMap** [DOCS]: answering "No" lets you "create a new risk directly" (January 2025 release). POA&M fields live on Action Items (2026 API) ([2025 notes](https://help.controlmap.io/hc/en-us/articles/33693378706843-2025-Release-Notes), [2026 notes](https://help.controlmap.io/hc/en-us/articles/46514811423771-2026-Release-Notes)).
- **Kaseya** [DOCS]:
  - Auto-generates a POA&M of "all discovered issues", but only after the "entire assessment process" is complete.
  - Regenerate archives the prior copy.
  - Source: [Plan of Action](https://www2.rapidfiretools.com/cm-grc/help/cm-grc-docs/cm-grc-plan-of-action.htm).
- **Users:** ControlMap community users asked to "attach risks to assessment questions" with no answer, which is demand for this link ([COMMUNITY](https://community.scalepad.com/controlmap-59/how-to-attach-risks-to-assessment-questions-4927)). Assessors like to see a drafted POA&M at assessment time (cmmc-tools §2.6).

**Verdict: PARTLY.**
- In-place creation with prefill is proven (Secureframe, Totem, ControlMap).
- **Automatic** creation on every NOT MET is not what the documented CMMC-specific tools do. Only Kaseya auto-generates, and only in bulk at the end.
- **Copy:**
  - A one-click "Add to POA&M" on NOT MET, prefilled, status Draft.
  - A persistent nudge or count of "NOT MET not on any POA&M" (Totem's advice).
  - The 180-day clock starts on a status change (Secureframe).
  - The eligibility flag from E3 sits on the draft.
- Auto-creating silently would clutter the POA&M during fieldwork, when many NOT METs are provisional.

### E5. Implementation statement per requirement feeds the SSP

**Who does it, and how:**
- **Totem** [DOCS]: "Implementation Details" is "the core of your SSP", captured per Organization Action (objective). The Dashboard has a "Security Plan Progress" widget (cmmc-tools §1.1).
- **FutureFeed** [DOCS]:
  - Control "Summary Notes" plus optional per-objective "Objective Statements" that "appear on the live SSP and the SSP Report" ([How to add objective statements](https://support.futurefeed.co/knowledge-base/hc/en-us/articles/27046731840276-how-to-add-objective-statements)).
  - SSP versions are approved with version notes; the approval logs name, date and time ([3.12.4 article](https://support.futurefeed.co/knowledge-base/hc/en-us/articles/32070785164948-addressing-3-12-4-update-the-ssp-regularly)).
- **Secureframe** [DOCS/MKT]: SPRS is "calculated live from your System Security Plan". The SSP Builder has version control; OSCAL export is marketing-only ([DOCS](https://support.secureframe.com/en/articles/15111372-understanding-your-sprs-score-in-secureframe), [MKT](https://secureframe.com/blog/announcing-secureframe-federal.md)).
- **ComplyUp:** Major/Minor revision or "untracked working copy" (cmmc-tools §1.3).
- **ControlMap** [DOCS]: an SSP report builder. Its July 2026 notes fixed "SSP report formatting", a reliability signal ([2026 notes](https://help.controlmap.io/hc/en-us/articles/46514811423771-2026-Release-Notes)).

**What users say:**
- FutureFeed templates are "good, but not great" [PRAC, conflicted](https://www.encomputers.com/2024/02/best-grc-cmmc/).
- IntelliGRC reports are "generic, overly broad" (cmmc-tools §1.8).

**Verdict: VALIDATED**, with one difference worth copying.
- The leaders capture text at **requirement level with optional objective-level statements** (FutureFeed), or fully per objective (Totem).
- A C3PAO examines per objective, so allow an optional per-objective statement under the requirement statement. Requirement-only text will read thin to an assessor.
- Also copy the "SSP completeness" meter (Totem).

### E6. Evidence library: upload or link once, map to many, reverse links, staleness warnings

**Who does it, and how:**
- **Map to many and versioning:**
  - Totem: link to "as many security requirements as you'd like"; a hash check blocks duplicate versions; links follow the new version ([DOCS](https://support.totem.tech/creating-artifacts/)).
  - FutureFeed: "write once, use everywhere" (cmmc-tools §1.2).
  - ControlMap: evidence requests map to objectives; can link to external locations so CUI stays out ([DOCS](https://help.controlmap.io/hc/en-us/articles/29270822904091-CMMC-Specific-Features)).
- **Reverse links ("used by N objectives"):** not documented by Totem. Hyperproof does this (README). This part is **PARTLY**.
- **Staleness warnings:**
  - **Vanta** [DOCS]: per-document renewal cadence; "Remind me this number of days before"; "Due soon" when the reminder is sent; "Overdue" after the date; nearing expiry still counts as passing ([Document renewal settings](https://help.vanta.com/en/articles/11345476-document-renewal-settings)).
  - **Drata** [DOCS]: renewal date defaults to 1 year; "Upcoming renewal" means within 2 months; once past the date, "the associated control will be no longer be ready" ([Evidence renewal date](https://help.drata.com/en/articles/13417542-evidence-renewal-date)).
  - **ControlMap** [DOCS]: evidence requests have recurrence and due dates; "Refresh Evidence" creates new requests and keeps history (msp-grc §2.2).
  - **FutureFeed**: recurring tasks with email reminders ([3.12.4 article](https://support.futurefeed.co/knowledge-base/hc/en-us/articles/32070785164948-addressing-3-12-4-update-the-ssp-regularly)).
  - **Totem**: none documented.
- **Coverage view:**
  - FutureFeed "Expected Documents": FutureFeed-defined document categories "that auditors commonly ask for", each fulfilled by one document, with a fulfilled/outstanding report ([DOCS](https://support.futurefeed.co/knowledge-base/internal-knowledgebase-administering-expected-documents-in-futurefeed-0)).
  - ControlMap ships C3PAO-sourced CSVs to create 320 evidence placeholders (msp-grc §2.2).
- **User pain:** ControlMap files attached to an answer do not become evidence, and a user question about it went unanswered ([COMMUNITY](https://community.scalepad.com/controlmap-59/how-to-attach-assessment-supporting-artifact-as-evidence-directly-in-controlmap-4641)). Ignyte's only G2 complaint was the upload workflow (cmmc-tools §1.5).

**Verdict: VALIDATED** (all four parts are proven somewhere).
- **Copy:**
  - Drata's rule that expired evidence downgrades readiness. That maps to "verified MET reverts to evidence-pending when its evidence expires", which ties E6 to E2.
  - Vanta's per-item "remind N days before".
  - FutureFeed's Expected Documents as a coverage checklist (a policy per family, SSP, network diagram, asset inventory…).
  - Evidence attached at an objective *is* library evidence (avoid ControlMap's split).

### E7. Deliver: watermarked drafts any time, issuable gap package with NOT MET items, one review-and-issue step with checklist, auto backup

**Who does it, and how:**
- **Drafts any time / regenerate:**
  - Kaseya: "Generate Reports" / "Regenerate Reports", downloadable as a .zip. It needs only "at least a basic assessment" for reports, but POA&M generation needs the full assessment (msp-grc §1.4).
  - ComplyUp: untracked working copy vs revision.
  - FutureFeed: deliverable "version history … saved so you can see the organization's progress" ([DOCS](https://support.futurefeed.co/knowledge-base/hc/en-us/articles/11748716719124-how-to-generate-deliverables)).
- **Watermark:** **no CMMC or GRC vendor documents a DRAFT watermark.** It is common in other document tools (an accounting example: [IRIS](https://www.iris.co.uk/?p=24743)). This detail is novel here; the risk is negligible.
- **Gap package with NOT MET items:**
  - Kaseya: Rapid Baseline report for prospects (msp-grc §1.1).
  - ControlMap: Pre-Assessment Report for prospect tenants without a licence (msp-grc §2.1).
  - FutureFeed: Cyber-Readiness Presentation.
  - Kaseya Assessment Report + SPRS Score Report + POA&M from a partial state (msp-grc §1.4).
  - Nobody gates reports on 110/110.
- **Single review/issue step:**
  - FutureFeed SSP: Generate → approve, with version notes; approval "automatically record[s] your name, date, and time" ([DOCS](https://support.futurefeed.co/knowledge-base/hc/en-us/articles/32070785164948-addressing-3-12-4-update-the-ssp-regularly)).
  - **No vendor documents a pre-issue checklist.**
- **Auto backup:** not applicable to cloud competitors. It is a desktop-specific need, so no validation is possible.

**Verdict: PARTLY.**
- Drafts any time, a gap package, and one-step approval with a logged approver are proven.
- The watermark and the issue checklist are novel but low-risk.
- **Copy:**
  - Kaseya's single .zip bundle.
  - FutureFeed's version notes plus an auto-stamped approver.
  - ComplyUp's Major/Minor revision.
- **Design the checklist as warnings, not blockers.** Examples: "12 MET without evidence", "3 NOT MET not on POA&M", "2 POA&M items ineligible under 170.21", "SSP statements missing for 4 requirements". Blocking checklists recreate the gating problem the README criticises.

### E8. Interview mode (walk a family or role) and keyboard-driven review

**Who does it, and how:**
- **Focused one-item mode next to a list:** Kaseya's wizard ("Next") plus "View All Questions as List" ([DOCS](https://www2.rapidfiretools.com/cm-grc/help/cm-grc-docs/cm-grc-begin-controls-assessment.htm)).
  - One Kaseya reviewer praised the "prompted questionnaire approach".
  - Another complained that moving away from a question-driven interface meant more time spent reading the standard (msp-grc §1.6, [REVIEW Capterra snippet](https://www.capterra.ca/reviews/194233/compliance-manager)).
- **Assessment methods:** ControlMap's audit module records Examine / Interview / Test per sub-objective ([MKT](https://www.scalepad.com/updates/controlmap-adds-sub-objective-level-cmmc-auditing-with-emass-ready-reporting)). It does not say whether interviewees are recorded.
- **Assigning questions to people:** Kaseya ("My Work" portal; SMEs get filtered logins, msp-grc §1.1). ComplyUp assigns requirements to team members (cmmc-tools §1.3).
- **Walk by role:** **no tool documents an interview session grouped by role.**
  - Practitioners do it: DeepSeas sends "control families and suggested roles" (cmmc-tools §2.2).
  - Redspin publishes interview question guides "from each domain" [PRAC](https://redspin.com/resource-center/cmmc-guides/).
- **Keyboard shortcuts:** no GRC vendor help page found (searched Vanta, Drata, Hyperproof and Secureframe).

**Verdict:**
- Interview by family: **PARTLY**. The focused-mode pattern is proven; walking by family is just a filter.
- Interview by role: **NOVEL**. It needs a role→requirement mapping that nobody ships. 800-171A lists interview objects generically, so you would have to author it. Medium effort, unproven value.
- Keyboard: **NOVEL**, low risk for a single-user desktop power tool.
- **Recommend:**
  - Ship family walk first.
  - Add an "interviewee(s)" field plus E/I/T notes per objective (DIBCAC DB columns, cmmc-tools §1.7).
  - Defer role walk until Johnathan asks for it.

### E9. Yearly reassessment carrying last year's answers forward as "needs revalidation"

**Who does it, and how:**
- **ControlMap Assessment Snapshots** [DOCS]:
  - "MSPs told us that refreshing assessments each year was repetitive and time-consuming."
  - Choose "Clear all answers" or "Keep all answers". "Either way, previous answers will be indicated from the last snapshot."
  - Snapshots can be viewed and restored.
  - Paid tiers only. Phase 1 shipped September 2025; phase 2 (view and restore) October 2025.
  - Sources: [Snapshots](https://help.controlmap.io/hc/en-us/articles/41951021929115-Working-with-Framework-Assessment-Snapshots), [2025 notes](https://help.controlmap.io/hc/en-us/articles/33693378706843-2025-Release-Notes).
- **Kaseya** (legacy) [DOCS]: "Use Previous Response" per field and "Use All Previous Responses" per form (msp-grc §1.7). Kaseya also imports Rapid Baseline answers through a side-by-side compare.
- **FutureFeed**: deliverable version history and SSP snapshots on a recurring task (links above).
- **Drata**: evidence expires on its renewal date and the control stops being "ready" (E6), which acts as automatic revalidation.
- **No tool has an explicit "needs revalidation" status** that blocks counting until it is confirmed. ControlMap's "keep" mode keeps answers counting.

**Verdict: VALIDATED** (carry-forward is proven and was built in response to MSP demand).
- The explicit revalidation state is a small, defensible extension. It fits E2: carried MET becomes provisional until reconfirmed.
- **Copy:** ControlMap's previous-answer display beside the current one, and the "keep or clear" choice at the start.

---

## 2. What proven tools do that the redesign misses

Ordered by relevance to the self-assessment path (Phase 2 is suspended).

1. **Asset inventory with CMMC asset categories, plus a CUI inventory.**
   - Totem: hardware inventory with a "CMMC Asset Category" field, and a CUI inventory with a six-phase handling lifecycle (cmmc-tools §1.1).
   - ControlMap: CUI tagging on assets (October 2025, [DOCS](https://help.controlmap.io/hc/en-us/articles/33693378706843-2025-Release-Notes)).
   - FutureFeed: Sensitive Data Inventory → tools (cmmc-tools §1.2).
   - 32 CFR 170.19 requires CUI, Security Protection, CRMA and Specialized assets in the asset inventory, the SSP *and* the network diagram ([REG](https://www.law.cornell.edu/cfr/text/32/170.19)).
   - The "Proposed shape" has a Profile questionnaire, but no asset inventory feeding the SSP. **High priority:** the SSP is incomplete without it.
2. **ESP / shared-responsibility inheritance.**
   - FutureFeed: "Inherited" objective status, with a yellow warning when no SRM is linked ([DOCS](https://support.futurefeed.co/knowledge-base/hc/en-us/articles/34734070131988-resolving-the-yellow-warning-for-inheritance-in-objectives)).
   - Totem: "Shared Responsibilities" field per objective ([MKT](https://www.totem.tech/cybersecurity-compliance-software/)).
   - ControlMap: "SRM identification and reporting" ([DOCS](https://help.controlmap.io/hc/en-us/articles/29270822904091-CMMC-Specific-Features)).
   - Most small DIB clients sit on GCC High or PreVeil with a vendor SRM. **High priority:** add an "Inherited (ESP: X)" answer that counts as MET when the SRM is linked.
3. **Policy and procedure templates.**
   - Totem: "dozens of customizable CMMC compliance artifact templates" ([MKT](https://www.totem.tech/cybersecurity-compliance-software/)).
   - ComplyUp: "14 800-171 Family-Specific Policies" (cmmc-tools §1.3).
   - FutureFeed: a third-party Document Templates add-on ([MKT](https://futurefeed.co/)).
   - Cynomi: auto-generated policies (msp-grc §3).
   - PreVeil sells a pre-written SSP pack (cmmc-tools §1.4).
   - **Medium priority.** It is a consultant revenue lever; it could be a template library rather than generation.
4. **SPRS submission helper.**
   - FutureFeed lists "SPRS Submissions" as a deliverable type ([DOCS](https://support.futurefeed.co/knowledge-base/hc/en-us/articles/11748716719124-how-to-generate-deliverables)).
   - ComplyUp's free scorer generates a ready-to-send SPRS email (cmmc-tools §1.3).
   - Secureframe has a help article on submitting to SPRS ([DOCS](https://support.secureframe.com/hc/en-us/articles/48612479537171-Submitting-Your-SPRS-Score-to-DoD)).
   - **Medium-high priority, cheap to build:** a one-page "SPRS entry sheet" with score, assessment date, scope/CAGE, SSP name and date, and POA&M completion date.
5. **Annual affirmation tracking.**
   - 32 CFR 170.22 requires an affirmation by the Affirming Official at the end of a self-assessment and annually after ([REG](https://www.law.cornell.edu/cfr/text/32/170.22)).
   - **No vendor documentation found for an affirmation tracker.** Practitioners recommend a reminder 30 days before the anniversary ([PRAC KLC](https://klcconsulting.net/cmmc-sprs-annual-affirmation/)).
   - **Gap in the market and in our design.** It fits the Home queue and the retained-client cadence directly. MORSECORP shows the cost of letting a posted score go stale (E2).
6. **Evidence placeholders / expected-evidence checklist.**
   - ControlMap: a C3PAO CSV of 320 placeholders.
   - FutureFeed: Expected Documents (E6).
   - Gives a coverage target before evidence exists.
7. **Partial-credit handling for 3.5.3 and 3.13.11.** Covered in E3. Make sure it is in scope; it is not called out in "Proposed shape".
8. **Evidence export grouped by objective, with hashing.**
   - ControlMap's "Evidence exporter with evidence grouped by objective".
   - FutureFeed's file-naming schema for the evidence ZIP ([DOCS](https://support.futurefeed.co/knowledge-base/hc/en-us/articles/37455704743316-file-naming-schema-for-the-evidence-files-export-zip-download)).
   - Hashing is done outside FutureFeed (cmmc-tools §1.2).
   - A desktop app can SHA-256 locally. **Medium priority** for C3PAO-prep later.
9. **Integrations / auto-answer with review.**
   - ControlMap Tech Stacks pre-answer questions from a product library "with a review step before any auto-answer is accepted" ([DOCS](https://help.controlmap.io/hc/en-us/articles/52057842170523-Tech-Stacks)).
   - Cynomi suggests answers "with confidence, reasoning and sources" for confirmation ([MKT](https://cynomi.com/platform/assessments/)).
   - This is the proven pattern for Johnathan's V2 Halo/NinjaOne direction. It confirms the "suggested vs confirmed" seam in the README. A reusable "client tech stack → pre-answered objectives" library is the MSP-scale version.
10. **eMASS / OSCAL export.**
    - ControlMap: eMASS-ready reporting, ">90% of report fields" (June 2026).
    - Secureframe: OSCAL SSP export (MKT).
    - **Low priority** while Phase 2 is suspended.
11. **Prospect / pre-sales assessment.**
    - ControlMap: a free pre-assessment for prospect tenants.
    - Kaseya: Rapid Baseline "positioned for sales prospecting" (msp-grc §1.1).
    - Fits "compliance as a service is a growth priority". The gap package (E7) could double as this.
12. **CRM.** None of the CMMC tools reviewed ship a sales CRM. They ship PSA ticket export instead (Kaseya → Autotask/myITprocess, msp-grc §1.4). **Not a gap**; the Halo PSA direction covers it.
13. **Client task assignment / evidence collection workflow.**
    - FutureFeed: task → evidence → sign → review.
    - ControlMap: evidence requests with assignee and due date.
    - Client access is V3 per Johnathan, so this is **deferred**. Keep a "waiting on client" state on the Home queue.

---

## 3. Verdict summary

| # | Element | Verdict | Main proof | Main adjustment |
|---|---|---|---|---|
| 1 | Requirement master-detail, objective rows | VALIDATED | Totem, Secureframe, ControlMap | Show per-requirement point value or deduction in the list |
| 2 | Provisional status + verified/projected scores | PARTLY (dual score NOVEL) | Totem Trending Met, Kaseya Rapid Baseline; MORSECORP FCA case supports a verified score | Verified is the headline, projected secondary; distinct status word |
| 3 | Live SPRS + arithmetic + 170.21 checks | VALIDATED / PARTLY (checks) | All tools have a live score; Secureframe claims eligibility flags | Literal arithmetic (avoid ControlMap's "+1" confusion); partial-credit modal |
| 4 | NOT MET → POA&M draft in place | PARTLY | Secureframe prefilled Draft; Totem "Add to POA&M" | One click, not auto; "NOT MET not on POA&M" nudge; 180-day clock on In Progress |
| 5 | Implementation statement → SSP | VALIDATED | Totem, FutureFeed, Secureframe | Allow optional per-objective statements |
| 6 | Evidence library + staleness | VALIDATED | Totem versioning, Vanta and Drata renewal, ControlMap refresh | Expiry reverts verified MET to pending |
| 7 | Deliver: drafts, gap package, one issue step | PARTLY | Kaseya, FutureFeed, ComplyUp | Checklist as warnings; watermark is novel but harmless |
| 8 | Interview mode + keyboard | PARTLY (family) / NOVEL (role, keyboard) | Kaseya wizard + list; ControlMap E/I/T | Family walk first; interviewee field; defer role walk |
| 9 | Yearly carry-forward, needs revalidation | VALIDATED | ControlMap Snapshots, Kaseya Use Previous | Show previous answer alongside; carried MET counts as provisional |

**Nothing was CONTRADICTED.** The closest is E4's "auto-create". The documented CMMC tools deliberately leave POA&M creation to the user (Secureframe: "you decide what is formally documented as a gap").

## 4. What I could not verify

- Any Reddit (r/CMMC), LinkedIn or webinar user commentary: blocked or not searched.
- G2/Capterra figures beyond search snippets. Secureframe/Vanta/Drata CMMC-specific review content.
- Secureframe's "flags requirements that can't be deferred" UI. It is marketing only; the help article does not describe it.
- Totem, FutureFeed, Exostar and Ignyte customer counts. FutureFeed's 1,400 clients is a vendor claim.
- Compliance Scorecard, Apptega and Cynomi CMMC workflow detail: no public docs found.
- Whether any vendor ships a DRAFT watermark, a pre-issue checklist, keyboard shortcuts, role-based interview sessions or affirmation tracking. Not found ≠ does not exist.
- The MORSECORP figures come from law-firm summaries and the relator's settlement-agreement PDF, not the justice.gov release itself.
