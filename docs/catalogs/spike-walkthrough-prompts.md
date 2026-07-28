# Walkthrough prompts — two sample standards

**Spike for GitHub issue #29. Not an approved catalog artefact.**

Two standards, one per source path, because the paths produce differently shaped prompts and both have to read well.

## What to tell me

1. **Does each path read well in the room?** The Security path gives you questions to ask. The Privacy path gives you requirements to check a document against. Both are legitimate; both need to work for you.
2. **Is the volume right?** 83 prompts across 5 records here. Extrapolated over 194 records that is several hundred. Structure, or noise?
3. **Security routing is settled.** This raw sample groups NIST questions under the standard. Production routes questions to the NIST-identified implementation specification and retains only genuinely standard-wide guidance on the parent. Review the volume, not the attachment rule.

## Provenance

| Source | Covers | Standing |
|---|---|---|
| NIST SP 800-66r2 | Security Rule (45 CFR 164.308-164.316) | Published NIST guidance. Secondary to the rule text. |
| 45 CFR Part 164 | Privacy Rule and Breach Notification Rule | The rules enumerate their own checklists. Prompts quote the regulation and are citable to a paragraph. |

_Prompts carry no status, produce no findings, and never appear in a report as assessable items. The determination stays on the record._

## Extraction warnings

- No enumerated sub-paragraphs found beneath 164.520(e).

---

# Security Rule path

This is raw pre-routing output grouped under the standard. The approved implementation routes a NIST key activity's questions to the implementation specification it identifies; genuinely standard-wide questions remain parent guidance. The standard-only attachment below is known superseded behavior.

## 45 CFR 164.308(a)(1)(i)

### Security management process

_Standard_

**Regulation text**

> Implement policies and procedures to prevent, detect, contain, and correct security violations.

**Determination** — one for this record

`Blank` · `Met` · `Not Met` · `Pending` · `N/A (rationale required)`

**Prompts** — 45

**Identify All ePHI and Relevant Information Systems**

- [ ] Has all ePHI generated, stored, processed, and transmitted within the organization been identified?
- [ ] Are all hardware and software for which the organization is responsible periodically inventoried?
- [ ] Is the hardware and software inventory updated on a regular basis?
- [ ] Have hardware and software that maintains or transmits ePHI been identified? Does this inventory include removable media and remote access devices?
- [ ] Is the current configuration of organizational systems documented, including connections to other systems?
- [ ] Has a BIA been performed?

**Conduct Risk Assessment** _(required)_

- [ ] Are there any prior risk assessments, audit comments, security requirements, and/or security test results?
- [ ] Is there intelligence available from agencies, the Office of the Inspector General (OIG), the United States Computer Emergency Readiness Team (US-CERT), virus alerts, and/or vendors?

**Implement a Risk Management Program** _(required)_

- [ ] Is executive leadership and/or management involved in risk management decisions?
- [ ] Has a risk management program been created with related policies?
- [ ] Does the regulated entity need to engage other resources (e.g., external expertise) to assist in risk management?
- [ ] Do current safeguards ensure the confidentiality, integrity, and availability of all ePHI?
- [ ] Do current safeguards protect against reasonably anticipated uses or disclosures of ePHI that are not permitted by the Privacy Rule?
- [ ] Has the regulated entity used the results of risk assessment and risk management processes to guide the selection and implementation of appropriate controls to protect ePHI?

**Acquire Information Technology (IT) Systems and Services**

- [ ] Will new security controls work with the existing IT architecture?
- [ ] Have the security requirements of the organization been compared to the security features of existing or proposed hardware and software?
- [ ] Has a cost-benefit analysis been conducted to determine the reasonableness of the investment given the security risks identified?
- [ ] Has a training strategy been developed?37

**Create and Deploy Policies and Procedures**

- [ ] Has the regulated entity documented an organizational risk assessment/management policy that outlines the duties, responsible parties, frequency, and required documentation of the risk management program?
- [ ] Are policies and procedures in place for security?
- [ ] Is there a formal (documented) system security plan?
- [ ] Is there a formal contingency plan?41

**• Create procedures to be followed to accomplish particular security-related tasks. • Establish a frequency for reviewing policy and procedures.**

- [ ] Is there a process for communicating policies and procedures to the affected employees?
- [ ] Are policies and procedures reviewed and updated as needed?

**Develop and Implement a Sanction Policy** _(required)_

- [ ] Does the regulated entity have existing sanction policies and procedures to meet the requirements of this implementation specification? If not, can existing sanction policies be modified to include language related to violations of these policies and procedures?
- [ ] Is there a formal process in place to address system misuse, abuse, and fraudulent activity?
- [ ] Have workforce members been made aware of policies concerning sanctions for inappropriate access, use, and disclosure of ePHI?
- [ ] Has the need and appropriateness of a tiered structure of sanctions that accounts for the magnitude of harm and possible types of inappropriate disclosures been considered?
- [ ] How will managers and workforce members be notified regarding suspect activity?

**Develop and Deploy the Information System Activity Review Process** _(required)_

- [ ] Is there a policy that establishes what reviews will be conducted?
- [ ] Are there corresponding procedures that describe the specifics of the reviews?
- [ ] Who is responsible for the overall process and results?43
- [ ] How often will reviews take place?
- [ ] How often will review results be analyzed?
- [ ] Has the regulated entity considered all available capabilities to automate the reviews?
- [ ] Where will audit information reside (e.g., separate server)? Will it be stored external to the organization (e.g., cloud service provider)?

**Develop Appropriate Standard Operating Procedures**

- [ ] How will exception reports or logs be reviewed?
- [ ] Where will monitoring reports and their reviews be documented and maintained?

**Implement the Information System Activity Review and Audit Process**

- [ ] What mechanisms will be implemented to assess the effectiveness of the review process (measures)?
- [ ] What is the plan to revise the review process when needed?

**Select a Security Official to be Assigned Responsibility for HIPAA Security**

- [ ] Who in the organization: o Oversees the development and communication of security policies and procedures? o Is responsible for conducting the risk assessment? o Is responsible for conducting risk management? o Handles the results of periodic security evaluations and continuous monitoring? o Directs IT security purchasing and investment? o Ensures that security concerns have been addressed in system implementation?
- [ ] Does the security official have adequate access and communications with senior officials in the organization, such as executives, chief information officers, chief compliance officers, and in-house counsel?
- [ ] Who in the organization is authorized to accept risks from systems on behalf of the organization?

**Assign and Document the Individual’s Responsibility**

- [ ] Is there a complete job description that accurately reflects assigned security duties and responsibilities?
- [ ] Have the staff members in the organization been notified as to whom to call in the event of a security problem?48

---

## 45 CFR 164.308(a)(1)(ii)(A) — **Required**

### Risk analysis

_Implementation specification_

Under: 45 CFR 164.308(a)(1)(i) — Security management process

**Regulation text**

> Conduct an accurate and thorough assessment of the potential risks and vulnerabilities to the confidentiality, integrity, and availability of electronic protected health information held by the covered entity or business associate.

**Determination** — one for this record

`Blank` · `Met` · `Not Met` · `Pending` · `N/A (rationale required)`

**Prompts** — none extracted for this record.

---

## 45 CFR 164.308(a)(1)(ii)(B) — **Required**

### Risk management

_Implementation specification_

Under: 45 CFR 164.308(a)(1)(i) — Security management process

**Regulation text**

> Implement security measures sufficient to reduce risks and vulnerabilities to a reasonable and appropriate level to comply with § 164.306(a).

**Determination** — one for this record

`Blank` · `Met` · `Not Met` · `Pending` · `N/A (rationale required)`

**Prompts** — none extracted for this record.

---

## 45 CFR 164.308(a)(1)(ii)(C) — **Required**

### Sanction policy

_Implementation specification_

Under: 45 CFR 164.308(a)(1)(i) — Security management process

**Regulation text**

> Apply appropriate sanctions against workforce members who fail to comply with the security policies and procedures of the covered entity or business associate.

**Determination** — one for this record

`Blank` · `Met` · `Not Met` · `Pending` · `N/A (rationale required)`

**Prompts** — none extracted for this record.

---

## 45 CFR 164.308(a)(1)(ii)(D) — **Required**

### Information system activity review

_Implementation specification_

Under: 45 CFR 164.308(a)(1)(i) — Security management process

**Regulation text**

> Implement procedures to regularly review records of information system activity, such as audit logs, access reports, and security incident tracking reports.

**Determination** — one for this record

`Blank` · `Met` · `Not Met` · `Pending` · `N/A (rationale required)`

**Prompts** — none extracted for this record.

---

---

# Privacy Rule path

This is raw pre-filter extraction of the sub-paragraphs the regulation enumerates. The approved implementation classifies each cited entry as an assessment check, applicability note, or context; only assessment checks render checkboxes. The raw checkboxes on exceptions, optional permissions, and structural lead-ins below are known incorrect output.

## 45 CFR 164.520(a)

### Notice of privacy practices

_Standard_

**Regulation text**

> (1) Right to notice. Except as provided by paragraph (a)(3) or (4) of this section, an individual has a right to adequate notice of the uses and disclosures of protected health information that may be made by the covered entity, and of the individual's rights and the covered entity's legal duties with respect to protected health information.

**Determination** — one for this record

`Blank` · `Met` · `Not Met` · `Pending` · `N/A (rationale required)`

**Prompts** — 5

**Notice requirements for covered entities creating or maintaining records subject to 42 U.S.C. 290dd-2**

- [ ] As provided in 42 CFR 2.22, an individual who is the subject of records protected under 42 CFR part 2 has a right to adequate notice of the uses and disclosures of such records, and of the individual's rights and the covered entity's legal duties with respect to such records.  
  <sub>45 CFR 164.520(a)(2)</sub>

**Exception for group health plans**

- [ ] (i) An individual enrolled in a group health plan has a right to notice:  
  <sub>45 CFR 164.520(a)(3)</sub>

- [ ] A group health plan that provides health benefits solely through an insurance contract with a health insurance issuer or HMO, and that creates or receives protected health information in addition to summary health information as defined in § 164.504(a) or information on whether the individual is participating in the group health plan, or is enrolled in or has disenrolled from a health insurance issuer or HMO offered by the plan, must:  
  <sub>45 CFR 164.520(a)(3)(ii)</sub>
- [ ] A group health plan that provides health benefits solely through an insurance contract with a health insurance issuer or HMO, and does not create or receive protected health information other than summary health information as defined in § 164.504(a) or information on whether an individual is participating in the group health plan, or is enrolled in or has disenrolled from a health insurance issuer or HMO offered by the plan, is not required to maintain or provide a notice under this section.  
  <sub>45 CFR 164.520(a)(3)(iii)</sub>

**Exception for inmates**

- [ ] An inmate does not have a right to notice under this section, and the requirements of this section do not apply to a correctional institution that is a covered entity.  
  <sub>45 CFR 164.520(a)(4)</sub>

---

## 45 CFR 164.520(b)

### Content of notice

_Implementation specification_

Under: 45 CFR 164.520(a) — Notice of privacy practices

**Regulation text**

> (1) Required elements. The covered entity, including any covered entity receiving or maintaining records subject to 42 U.S.C. 290dd-2, must provide a notice that is written in plain language and that contains the elements required by this paragraph.

**Determination** — one for this record

`Blank` · `Met` · `Not Met` · `Pending` · `N/A (rationale required)`

**Prompts** — 12

**Header**

- [ ] The notice must contain the following statement as a header or otherwise prominently displayed:  
  <sub>45 CFR 164.520(b)(1)(i)</sub>

- [ ] “THIS NOTICE DESCRIBES HOW MEDICAL INFORMATION ABOUT YOU MAY BE USED AND DISCLOSED AND HOW YOU CAN GET ACCESS TO THIS INFORMATION. PLEASE REVIEW IT CAREFULLY.”  
  <sub>45 CFR 164.520(b)(1)(i)</sub>
- [ ] For the covered entity to apply a change in its more limited uses and disclosures to protected health information created or received prior to issuing a revised notice, in accordance with § 164.530(i)(2)(ii), the notice must include the statements required by paragraph (b)(1)(v)(C) of this section.  
  <sub>45 CFR 164.520(b)(2)(ii)</sub>

**Uses and disclosures**

- [ ] The notice must contain:  
  <sub>45 CFR 164.520(b)(1)(ii)</sub>

**Separate statements for certain uses or disclosures**

- [ ] If the covered entity intends to engage in any of the following activities, the description required by paragraph (b)(1)(ii)(A) or (B) of this section must include a separate statement informing the individual of such activities, as applicable:  
  <sub>45 CFR 164.520(b)(1)(iii)</sub>

**Individual rights**

- [ ] The notice must contain a statement of the individual's rights with respect to protected health information and a brief description of how the individual may exercise these rights, as follows:  
  <sub>45 CFR 164.520(b)(1)(iv)</sub>

**Covered entity's duties**

- [ ] The notice must contain:  
  <sub>45 CFR 164.520(b)(1)(v)</sub>

**Complaints**

- [ ] The notice must contain a statement that individuals may complain to the covered entity and to the Secretary if they believe their privacy rights have been violated, a brief description of how the individual may file a complaint with the covered entity, and a statement that the individual will not be retaliated against for filing a complaint.  
  <sub>45 CFR 164.520(b)(1)(vi)</sub>

**Contact**

- [ ] The notice must contain the name, or title, and telephone number of a person or office to contact for further information as required by § 164.530(a)(1)(ii).  
  <sub>45 CFR 164.520(b)(1)(vii)</sub>

**Effective date**

- [ ] The notice must contain the date on which the notice is first in effect, which may not be earlier than the date on which the notice is printed or otherwise published.  
  <sub>45 CFR 164.520(b)(1)(viii)</sub>

**Optional elements**

- [ ] (i) In addition to the information required by paragraph (b)(1) of this section, if a covered entity elects to limit the uses or disclosures that it is permitted to make under this subpart, the covered entity may describe its more limited uses or disclosures in its notice, provided that the covered entity may not include in its notice a limitation affecting its right to make a use or disclosure that is required by law or permitted by § 164.512(j)(1)(i).  
  <sub>45 CFR 164.520(b)(2)</sub>

**Revisions to the notice**

- [ ] The covered entity must promptly revise and distribute its notice whenever there is a material change to the uses or disclosures, the individual's rights, the covered entity's legal duties, or other privacy practices stated in the notice. Except when required by law, a material change to any term of the notice may not be implemented prior to the effective date of the notice in which such material change is reflected.  
  <sub>45 CFR 164.520(b)(3)</sub>

---

## 45 CFR 164.520(c)

### Provision of notice

_Implementation specification_

Under: 45 CFR 164.520(a) — Notice of privacy practices

**Regulation text**

> A covered entity must make the notice required by this section available on request to any person and to individuals as specified in paragraphs (c)(1) through (c)(3) of this section, as applicable.

**Determination** — one for this record

`Blank` · `Met` · `Not Met` · `Pending` · `N/A (rationale required)`

**Prompts** — 14

**Specific requirements for health plans**

- [ ] (i) A health plan must provide the notice:  
  <sub>45 CFR 164.520(c)(1)</sub>

- [ ] No less frequently than once every three years, the health plan must notify individuals then covered by the plan of the availability of the notice and how to obtain the notice.  
  <sub>45 CFR 164.520(c)(1)(ii)</sub>
- [ ] The health plan satisfies the requirements of paragraph (c)(1) of this section if notice is provided to the named insured of a policy under which coverage is provided to the named insured and one or more dependents.  
  <sub>45 CFR 164.520(c)(1)(iii)</sub>
- [ ] If a health plan has more than one notice, it satisfies the requirements of paragraph (c)(1) of this section by providing the notice that is relevant to the individual or other person requesting the notice.  
  <sub>45 CFR 164.520(c)(1)(iv)</sub>
- [ ] If there is a material change to the notice:  
  <sub>45 CFR 164.520(c)(1)(v)</sub>
- [ ] Provide the notice:  
  <sub>45 CFR 164.520(c)(2)(i)</sub>
- [ ] Except in an emergency treatment situation, make a good faith effort to obtain a written acknowledgment of receipt of the notice provided in accordance with paragraph (c)(2)(i) of this section, and if not obtained, document its good faith efforts to obtain such acknowledgment and the reason why the acknowledgment was not obtained;  
  <sub>45 CFR 164.520(c)(2)(ii)</sub>
- [ ] If the covered health care provider maintains a physical service delivery site:  
  <sub>45 CFR 164.520(c)(2)(iii)</sub>
- [ ] Whenever the notice is revised, make the notice available upon request on or after the effective date of the revision and promptly comply with the requirements of paragraph (c)(2)(iii) of this section, if applicable.  
  <sub>45 CFR 164.520(c)(2)(iv)</sub>
- [ ] A covered entity may provide the notice required by this section to an individual by e-mail, if the individual agrees to electronic notice and such agreement has not been withdrawn. If the covered entity knows that the e-mail transmission has failed, a paper copy of the notice must be provided to the individual. Provision of electronic notice by the covered entity will satisfy the provision requirements of paragraph (c) of this section when timely made in accordance with paragraph (c)(1) or (2) of this section.  
  <sub>45 CFR 164.520(c)(3)(ii)</sub>
- [ ] For purposes of paragraph (c)(2)(i) of this section, if the first service delivery to an individual is delivered electronically, the covered health care provider must provide electronic notice automatically and contemporaneously in response to the individual's first request for service. The requirements in paragraph (c)(2)(ii) of this section apply to electronic notice.  
  <sub>45 CFR 164.520(c)(3)(iii)</sub>
- [ ] The individual who is the recipient of electronic notice retains the right to obtain a paper copy of the notice from a covered entity upon request.  
  <sub>45 CFR 164.520(c)(3)(iv)</sub>

**Specific requirements for certain covered health care providers**

- [ ] A covered health care provider that has a direct treatment relationship with an individual must:  
  <sub>45 CFR 164.520(c)(2)</sub>

**Specific requirements for electronic notice**

- [ ] (i) A covered entity that maintains a web site that provides information about the covered entity's customer services or benefits must prominently post its notice on the web site and make the notice available electronically through the web site.  
  <sub>45 CFR 164.520(c)(3)</sub>

---

## 45 CFR 164.520(d)

### Joint notice by separate covered entities

_Implementation specification_

Under: 45 CFR 164.520(a) — Notice of privacy practices

**Regulation text**

> Covered entities that participate in organized health care arrangements may comply with this section by a joint notice, provided that:

**Determination** — one for this record

`Blank` · `Met` · `Not Met` · `Pending` · `N/A (rationale required)`

**Prompts** — 7

- [ ] The covered entities participating in the organized health care arrangement agree to abide by the terms of the notice with respect to protected health information created or received by the covered entity as part of its participation in the organized health care arrangement;  
  <sub>45 CFR 164.520(d)(1)</sub>
- [ ] The joint notice meets the implementation specifications in paragraph (b) of this section, except that the statements required by this section may be altered to reflect the fact that the notice covers more than one covered entity; and  
  <sub>45 CFR 164.520(d)(2)</sub>
- [ ] Describes with reasonable specificity the covered entities, or class of entities, to which the joint notice applies;  
  <sub>45 CFR 164.520(d)(2)(i)</sub>
- [ ] Describes with reasonable specificity the service delivery sites, or classes of service delivery sites, to which the joint notice applies; and  
  <sub>45 CFR 164.520(d)(2)(ii)</sub>
- [ ] If applicable, states that the covered entities participating in the organized health care arrangement will share protected health information with each other, as necessary to carry out treatment, payment, or health care operations relating to the organized health care arrangement.  
  <sub>45 CFR 164.520(d)(2)(iii)</sub>
- [ ] The covered entities included in the joint notice must provide the notice to individuals in accordance with the applicable implementation specifications of paragraph (c) of this section. Provision of the joint notice to an individual by any one of the covered entities included in the joint notice will satisfy the provision requirement of paragraph (c) of this section with respect to all others covered by the joint notice.  
  <sub>45 CFR 164.520(d)(3)</sub>
- [ ] The permission in paragraph (d) of this section for covered entities that participate in an organized health care arrangement to issue a joint notice may not be construed to remove any obligations or duties of entities creating or maintaining records subject to 42 U.S.C. 290dd-2, or to remove any rights of patients who are the subjects of such records.  
  <sub>45 CFR 164.520(d)(4)</sub>

---

## 45 CFR 164.520(e)

### Documentation

_Implementation specification_

Under: 45 CFR 164.520(a) — Notice of privacy practices

**Regulation text**

> A covered entity must document compliance with the notice requirements, as required by § 164.530(j), by retaining copies of the notices issued by the covered entity and, if applicable, any written acknowledgments of receipt of the notice or documentation of good faith efforts to obtain such written acknowledgment, in accordance with paragraph (c)(2)(ii) of this section.

**Determination** — one for this record

`Blank` · `Met` · `Not Met` · `Pending` · `N/A (rationale required)`

**Prompts** — none extracted for this record.

---

## If the answer to question 1 is no

Stop. The approach needs rethinking and ingesting 184 more records would not have helped.
