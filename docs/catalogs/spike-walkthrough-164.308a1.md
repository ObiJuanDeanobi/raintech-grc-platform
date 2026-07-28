# Walkthrough sample — 45 CFR 164.308(a)(1) Security Management Process

**Spike for GitHub issue #29. Not an approved catalog artefact.**

One question to answer while reading this: **could you run this with a client in the room?** Not whether the wording is perfect — whether the shape of it works.

## How to read it

Each **record** is a citable unit of 45 CFR Part 164 and carries exactly one determination. That is what ends up in a report and what a finding attaches to.

The **prompts** beneath it are what you actually ask and look at. They carry no status of their own, produce no findings, and never appear in a report as assessable items. They exist to structure the conversation — the job CMMC assessment objectives do for you today.

The checkboxes on prompts are working aids for the walkthrough, not determinations.

## Provenance

| | |
|---|---|
| Record text and citations | eCFR versioner API, Title 45 Part 164, snapshot 2026-07-01 |
| Prompts | HHS OCR HIPAA Audit Protocol, revision July 2018 |
| Prompts retrieved | 2026-07-28 |

_Guidance, not regulation. 45 CFR Part 164 as published on eCFR is controlling. Where the protocol and the rule text disagree, the rule text wins._

## Extraction limitation — read this before judging coverage

**Coverage: 2 of 4 implementation specifications under 45 CFR 164.308(a)(1).**

The protocol is published as a filterable web page rather than a structured download. Repeated fetches returned different truncations of the document, and entries for 164.308(a)(1)(ii)(C) and (D) could not be retrieved reliably. Those two records are deliberately left without prompts rather than filled with invented text.

The two records without prompts are shown as they are. Judge the model on the two that are populated; the gaps are an extraction problem, not a modelling one.

---

## 45 CFR 164.308(a)(1)(i)

### Security management process

_Standard_

**Regulation text**

> Implement policies and procedures to prevent, detect, contain, and correct security violations.

**Determination** — one for this record

`Blank`  ·  `Met`  ·  `Not Met`  ·  `Pending`  ·  `N/A (rationale required)`

**Walkthrough prompts** — none. The standard's status derives from its implementation specifications. The protocol attaches its inquiries to the specifications, not to the standard, which matches the rollup rule already in the specification.

---

## 45 CFR 164.308(a)(1)(ii)(A) — **Required**

### Risk analysis

_Implementation specification_

Under: 45 CFR 164.308(a)(1)(i) — Security management process

**Regulation text**

> Conduct an accurate and thorough assessment of the potential risks and vulnerabilities to the confidentiality, integrity, and availability of electronic protected health information held by the covered entity or business associate.

**Established performance criteria** _(OCR Audit Protocol)_

> Conduct an accurate and thorough assessment of the potential risks and vulnerabilities to the confidentiality, integrity, and availability of electronic protected health information held by the covered entity.

**Key activity** _(OCR Audit Protocol)_ — Conduct Risk Assessment

**Determination** — one for this record

`Blank`  ·  `Met`  ·  `Not Met`  ·  `Pending`  ·  `N/A (rationale required)`

**Walkthrough prompts** _(OCR Audit Protocol — no status of their own)_

- [ ] Inquire of management as to whether formal or informal policies or practices exist to conduct an accurate assessment of potential risks and vulnerabilities to the confidentiality, integrity, and availability of ePHI.
- [ ] Obtain and review relevant documentation and evaluate the content relative to the specified criteria for an assessment of potential risks and vulnerabilities of ePHI.
- [ ] Evidence of covered entity risk assessment process or methodology considers the elements in the criteria and has been updated or maintained to reflect changes in the covered entity's environment.
- [ ] Determine if the covered entity risk assessment has been conducted on a periodic basis.
- [ ] Determine if the covered entity has identified all systems that contain, process, or transmit ePHI.

---

## 45 CFR 164.308(a)(1)(ii)(B) — **Required**

### Risk management

_Implementation specification_

Under: 45 CFR 164.308(a)(1)(i) — Security management process

**Regulation text**

> Implement security measures sufficient to reduce risks and vulnerabilities to a reasonable and appropriate level to comply with § 164.306(a).

**Established performance criteria** _(OCR Audit Protocol)_

> Implement security measures sufficient to reduce risks and vulnerabilities to a reasonable and appropriate level to comply with § 164.306(a).

**Key activity** _(OCR Audit Protocol)_ — Implement a Risk Management Program

**Determination** — one for this record

`Blank`  ·  `Met`  ·  `Not Met`  ·  `Pending`  ·  `N/A (rationale required)`

**Walkthrough prompts** _(OCR Audit Protocol — no status of their own)_

- [ ] Inquire of management as to whether current security measures are sufficient to reduce risks and vulnerabilities to a reasonable and appropriate level to comply with § 164.306(a).
- [ ] Obtain and review security policies and evaluate the content relative to the specified criteria.
- [ ] Determine if the security policy has been approved and updated on a periodic basis.
- [ ] Determine if security standards address data moved within the organization and data sent out of the organization.

---

## 45 CFR 164.308(a)(1)(ii)(C) — **Required**

### Sanction policy

_Implementation specification_

Under: 45 CFR 164.308(a)(1)(i) — Security management process

**Regulation text**

> Apply appropriate sanctions against workforce members who fail to comply with the security policies and procedures of the covered entity or business associate.

**Determination** — one for this record

`Blank`  ·  `Met`  ·  `Not Met`  ·  `Pending`  ·  `N/A (rationale required)`

**Walkthrough prompts** — none. No prompts retrieved. The protocol entry exists but could not be extracted reliably from the published page. Left empty rather than invented.

---

## 45 CFR 164.308(a)(1)(ii)(D) — **Required**

### Information system activity review

_Implementation specification_

Under: 45 CFR 164.308(a)(1)(i) — Security management process

**Regulation text**

> Implement procedures to regularly review records of information system activity, such as audit logs, access reports, and security incident tracking reports.

**Determination** — one for this record

`Blank`  ·  `Met`  ·  `Not Met`  ·  `Pending`  ·  `N/A (rationale required)`

**Walkthrough prompts** — none. No prompts retrieved. Same limitation as (C).

---

## What to tell me

1. **Does the shape work?** One determination on the record, prompts beneath it that structure the conversation.
2. **Is the prompt volume right?** Risk analysis has five. Across 192 records this runs to several hundred. Useful structure, or noise?
3. **Is anything missing** that you would want in front of you at the moment of determining this record?

If the answer to 1 is no, stop — the approach needs rethinking and ingesting 191 more records would not have helped.
