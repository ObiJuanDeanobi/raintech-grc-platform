# Compliance-as-a-service validation: second-pass competitor research

Research date: 2026-10-08. This builds on `docs/research/2026-10-competitor-ux/msp-grc.md`, which covered assessment UX. This pass covers recurring service delivery, PSA/RMM integration, and practitioner signal. It does not repeat assessment-UX findings except where they bear on the verdicts.

**Source labels**
- **[HELP]**: vendor help center, knowledge base, or release notes.
- **[API]**: vendor API reference or OpenAPI/Swagger spec, read directly.
- **[MKT]**: vendor marketing page, blog, or press release.
- **[3P]**: press, review, or analysis by a third party. Flagged where a competitor or sponsor wrote it.
- **[REG]**: regulation text.
- **[PRACT]**: practitioner voice (community post, podcast, webinar quote).

**Access limits**
- Reddit (r/msp) returned no results through search, and its JSON API was blocked from this environment. **There are no verified Reddit quotes in this file.**
- Compliance Scorecard's marketing site returned 403. Its public Confluence docs (`compliancerisk.atlassian.net/wiki/spaces/CRIODOCS`) were readable through the Confluence REST API, so its coverage is strong.
- ControlMap help articles were read through the Zendesk Help Center API, as in the first pass.
- Apptega community posts were read through the Vanilla API.
- Kaseya Compliance Manager GRC help was read directly. Its table of contents came from the MadCap TOC file.
- The NinjaOne OpenAPI spec (`app.ninjarmm.com/apidocs/NinjaRMM-API-v2.json`) and the Halo Swagger spec (`halo.halopsa.com/api/swagger/v2/swagger.json`) were downloaded and parsed. **Neither API was called against a live tenant.**
- The Resolver regulatory-content article returned 403. The eCFR API refused requests from this environment, so CMMC scoping cites the existing repo note instead.

---

## 1. Tool-by-tool: how each supports managed or continuous compliance

### 1.1 ScalePad ControlMap (+ Lifecycle Manager)
- **Recurring and calendar work**
  - Evidence requests carry an assignee, a due date, and a recurrence. "Refresh Evidence" re-issues requests for the next cycle and keeps history. [HELP] https://help.controlmap.io/hc/en-us/articles/18164819008539-Working-with-Evidence
  - Policy documents have a **Review Date**. When it passes, ControlMap "automatically changes the status of policies, procedures, and governance documents from Approved to In Review." Re-approving forces a new review date. [HELP] https://help.controlmap.io/hc/en-us/articles/52451450118811-Document-automatically-moved-to-In-Review-after-review-date-passed
  - Policies and procedures can be "refreshed periodically by setting a refresh schedule." [HELP] https://help.controlmap.io/hc/en-us/articles/18157487719835-Automating-your-compliance-operations
  - Weekly reminder emails for policies and evidence are set per user. They summarize "relevant items across your environment." [HELP] https://help.controlmap.io/hc/en-us/articles/52180811220251-Managing-weekly-policy-and-evidence-reminder-emails-in-ControlMap
- **Multi-client view:** MSP Multi-Tenant Dashboard and Client Dashboard (Summary / ToDo Kanban / Comparison). Covered in the first pass. [HELP] https://help.controlmap.io/hc/en-us/articles/35547294075803-Client-Dashboard
- **Meetings and roadmap:** these are not handled inside ControlMap. A ControlMap **action item can be linked to a Lifecycle Manager Pro "initiative"** with a required Title, Status, and Schedule (year + quarter), which then "is created in Lifecycle Manager and added to the client's roadmap" (July 2026, phase 1). [HELP] https://help.controlmap.io/hc/en-us/articles/53077143937307-Link-ControlMap-Action-Items-to-Lifecycle-Manager-Pro-Initiatives
  - Lifecycle Manager's "client strategy dashboard" is the "hub" for QBR and vCIO meetings. It lets you "log meeting notes, store and update key contact information" and publish **Action Items that "can be automatically submitted as tickets in your ConnectWise Manage PSA"** (May 2024). [MKT] https://www.scalepad.com/updates/lifecycle-manager-introduces-client-engagement
- **Client portal:** a tenant portal for client users, who do not see Initiatives. [HELP, Lifecycle Manager link above] There is also a ControlMap-branded compliance portal on the Free tier. [HELP] https://help.controlmap.io/hc/en-us/articles/39891328764059-ControlMap-Tiers-Free-Essentials-Pro
- **Regulatory change:** framework content updates are announced in release notes, for example "Essential 8 framework has been updated" (January 2024). No per-client "you've been told" record was found. [HELP / community] https://community.scalepad.com/product-updates/controlmap-release-notes-january-2024-3031
- **Packaging hints:** Free (unlimited clients, one framework per client, one assessment, one report) → **Essentials, "designed to deliver compliance assessments as a service at an economical price"** (single framework) → Pro (unlimited frameworks, SSP/SPRS tools, automation). [HELP, Tiers link] The vendor also runs fortnightly onboarding sessions and office hours. [HELP] https://help.controlmap.io/hc/en-us/articles/20420178701467-Getting-Started-with-Webinars-and-Workshops

### 1.2 Compliance Scorecard (Compliance Risk), MSP-native "governance as a service"
- **Recurring and calendar work**
  - **Project Center**: Project Lists (per client), Milestones (completion is "calculated automatically based on how many milestone tasks are done"), and **Project Templates** "you build once and deploy across clients… like a CMMC readiness checklist or an annual audit preparation project." Templates import from CSV. [HELP] https://compliancerisk.atlassian.net/wiki/spaces/CRIODOCS/pages/434503682/Project+Center ; https://compliancerisk.atlassian.net/wiki/spaces/CRIODOCS/pages/934281222/Project+Templates ; https://compliancerisk.atlassian.net/wiki/spaces/CRIODOCS/pages/934313996/Milestones
  - The policy model is the "4 As": **Alignment, Authorization, Adoption (e-signature), Assessment ("a review date has been set")**. [HELP] https://compliancerisk.atlassian.net/wiki/spaces/CRIODOCS/pages/77398019/Dashboard
  - **Adoption campaigns** send policies, an optional video, a knowledge check, and an e-signature acknowledgment to a client audience, with reminders. Scheduled sending arrived in v10.0 (February 2026). [HELP] https://compliancerisk.atlassian.net/wiki/spaces/CRIODOCS/pages/882933762/Adoption+Campaign ; https://compliancerisk.atlassian.net/wiki/spaces/CRIODOCS/pages/737083399/Version+10.0.0+Release+Notes+2+16+2026
  - Asset lists sync from RMMs on a chosen "sync frequency and day" (see section 2). [HELP]
- **Multi-client dashboard:** "an overview of all your most critical activity across all your different company clients… policies, assessments, pending tasks, and risk matrix," with a Client Overview widget. Customizable since v10. [HELP, Dashboard link; v10 notes]
- **Client reporting:** v10 "AI Reports" generate a gap analysis, an **Executive Summary**, or a remediation action plan per client, with a Report History tab. [HELP, v10 notes] **POA&M** is generated from risks set to Mitigate or Transfer, with start/end dates, a responsible contact, a milestone, status, and **cost**, and exports to PDF/CSV. POA&M items can be pushed to Project Center lists. [HELP] https://compliancerisk.atlassian.net/wiki/spaces/CRIODOCS/pages/923500576/POAM
- **Responsibility:** each control can be marked as owned by the MSP, the company, or shared, with a vendor or tool as reference, plus a **RACI** per control. Controls or the whole assessment can be "opened to client." Assessments are versioned ("New assessments start at version 1.0"). [HELP] https://compliancerisk.atlassian.net/wiki/spaces/CRIODOCS/pages/125075464/Assessment+Events
- **Client portal:** per-client feature visibility. Clients can see their tool stack, tool costs, and "Available Tools… (upsell)." [HELP] https://compliancerisk.atlassian.net/wiki/spaces/CRIODOCS/pages/911835139/Client+Settings
- **Regulatory change:** no in-product change feed was found. What exists instead is a paid **Peer Group** with "weekly peer GRC accountability calls" and "nuanced insights into the regulatory landscape." That is education for the MSP, not a per-client log. [HELP] https://compliancerisk.atlassian.net/wiki/spaces/CRIODOCS/pages/76283969/Peer+group
- **Packaging hints:** a "Kickstart Bundle" sold as a one-time charge plus a recurring price (v9.2.6 notes). [HELP] https://compliancerisk.atlassian.net/wiki/spaces/CRIODOCS/pages/649428993/Version+9.2.6+Release+Notes+12+2+2025 It is available on Pax8. [3P, first pass]

### 1.3 Cynomi (AI vCISO platform)
- **Recurring work:** findings become "prioritized tasks and remediation plans," and Cynomi will "automatically attach evidence of task completion." [MKT] https://cynomi.com/platform/integrations/
- **Client reporting:** branded, exportable status and progress reports. Its "first 100 days" guidance puts **monthly progress communication** in the Report phase. [MKT] https://cynomi.com/blog/vciso-first-100-days/ A sponsored guide says reports should be an "executive summary, risk assessment, recommendations, strategic roadmap" and act as a due-diligence record "in audits, incident accountability reviews, and client disputes." [3P, sponsored by Cynomi] https://thehackernews.com/2025/01/taking-pain-out-of-cybersecurity.html
- **Meetings, regulatory-change alerts, client portal:** no documentation found. Framework content is "dynamic, always up to date" (podcast summary). [3P] https://telecomresellerpodcast.podcast.show/episode/135536541
- **Packaging (vendor guide, April 2026):** Core advisory, $1,000–1,500/month ("Annual assessment, quarterly reviews, basic policy set, executive summary"). Full vCISO, $2,000–3,500/month ("continuous posture tracking… risk register, remediation roadmaps, QBR-ready reporting"). Strategic, $3,500–5,000/month. Recommends a "$1,500 minimum" and monthly billing over hourly. [MKT] https://cynomi.com/blog/vciso-pricing-models-for-msps-how-to-price-security-advisory-services-in-2026/

### 1.4 Kaseya Compliance Manager GRC
- **Continuous work:** "Compliance Monitor" for "continuous, ongoing assessments using Discovery Agents," mass-deployed through Datto RMM or VSA. [HELP] https://www2.rapidfiretools.com/cm-grc/help/cm-grc-docs/compliance-monitor/cm-grc-with-compliance-monitor-quick-start.htm
- **Year-over-year:** **Archive Assessment** keeps an interactive snapshot of surveys, technical review, and reports. It is blocked while scans or "outstanding tasks" are in progress. [HELP] https://www2.rapidfiretools.com/cm-grc/help/cm-grc-docs/enhanced-archived-assessments.htm Combined with "Use Previous Response" (first pass), this is the annual carry-forward.
- **Multi-client:** Multi-sites view shows standards, last 5 scans, technical review status, Rapid Baseline / Controls / Requirements status, and the date reports were last generated. It is a status board, not a work queue. [HELP] https://www2.rapidfiretools.com/cm-grc/help/cm-grc-docs/multi-sites-view-cmgrc.htm
- **Portals:** Employee Portal (policy acknowledgment) and Vendor Portal (in TOC). [HELP] https://www2.rapidfiretools.com/cm-grc/help/cm-grc-docs/cm-grc-employee-portal.htm
- **Meetings, regulatory-change alerts, recurring-task calendar:** none found in the help TOC.

### 1.5 Apptega
- **Recurring tasks (December 2024):** for example, "review a sub-control from NIST 800-171 on the last Thursday of every month… no end date." Each instance auto-fills owner, milestones, and objective evidence, and sends a "reminder one week before the due date." [HELP / community] https://community.apptega.com/discussion/143/introducing-task-recurrence
- **Scheduled reports:** Report Name, Type, **Frequency**, Start/End, and time, emailed to users. [HELP / community] https://community.apptega.com/discussion/104/tip-tuesday-how-to-schedule-a-report
- **Regulatory change:** framework "packs" are rebuilt and announced on the community, for example GDPR (July 2026) and SOC 2 (March 2026). These are content updates, not per-client notices. [HELP / community] https://community.apptega.com/discussion/225/gdpr-framework-assessment-and-task-pack-rebuild-available-july-14th
- **Positioning:** "Compliance Guides" for MSPs and vCISOs include "How to maintain compliance over time (not just at audit time)," with HIPAA Security and CMMC v2.13 among them. They also mention the pain point "'Are we compliant?' turns into a long meeting." [MKT / community] https://community.apptega.com/discussion/212/new-in-apptega-15-complete-compliance-guides-to-standardize-delivery-and-prove-compliance-faster

### 1.6 Hyperproof (not MSP-specific; best-documented recurrence and staleness model)
- **Repeating tasks:** daily, weekly, monthly, quarterly, semiannual, or annual. They attach to a control, label, or risk, and can be event-triggered (for example, a failed automated test). Gotcha: deactivating the template owner stops generation. [HELP] https://docs.hyperproof.io/cm/en/work-items/repeating-tasks-overview (as of 2026-10 this redirects to help.hyperproof.app; content quoted from search index)
- **Freshness:** an expiration period on a control or label. Status goes Fresh → Expired either "on a recurring schedule" or "a set number of days after the object is marked fresh." There are dashboard widgets for Expired / Unknown / Fresh / Not set. When freshness expires, the control manager decides and creates a task. [HELP] https://docs.hyperproof.io/cm/en/best-practices/collect-proof-intro/collect-proof-freshness ; https://docs.hyperproof.io/admin/en/getting-started/turning-on-freshness
- **Regulatory change:** "added 173 new requirements to its HIPAA program" (August 2025), announced only in release notes. [HELP] https://help.hyperproof.app/en/articles/14303733-release-notes-2025-aug-21

### 1.7 Drata and Vanta (MSP programs)
- Drata: custom tasks recur "on a regular cadence," but "Recurrence only applies to custom tasks" (May 2025). [HELP] https://drata.com/updates/week-of-may-26 Multi-Instance Management for vCISOs and MSSPs dates from 2023 (first pass). [MKT] https://drata.com/blog/introducing-multi-instance-management
- Vanta: an MSP partner program exists. No public console documentation was found (first pass). Neither documents meeting, regulatory-change, or SPRS features.

### 1.8 HIPAA-for-MSP specialists
- **Compliancy Group ("The Guard"):** MSPs act as Affiliate (referral commission) or Reseller ("package The Guard with their own security… services"). "Compliancy Group always handles the implementation… our team of compliance coaches manage the regulatory requirements." The method is "Achieve, Illustrate, Maintain." Maintain-phase mechanics are **not verified**. [MKT] https://compliancy-group.com/hipaa-compliance-as-a-service/ ; https://compliancy-group.com/compliance-for-clients
- **Accountable (accountablehq.com):** partners "manage dozens or hundreds of clients from a single Accountable dashboard." "Each client gets their own compliance workspace." "HIPAA compliance isn't a one-time project — it's an ongoing need that drives predictable revenue." Partner pricing is **not public**. [MKT] https://accountablehq.com/partnerships ; [HELP] https://docs.accountablehq.com/docs/overview-of-accountablehq
- Both sell a **done-for-you HIPAA program the MSP resells**. Neither is a consultant workbench. That is a different model from Johnathan's: he is the coach.

### 1.9 Verification of named or other vCISO tools
| Name | Verdict | Evidence |
|---|---|---|
| **Galactic** | **Real (Galactic Advisors, now galacticsecurity.com), but not a GRC/CaaS workflow tool.** It sells MSP security testing: "CyberWatch runs recurring assessments across every client," monthly vulnerability checks, reporting, and a community (Weekly Power Hour, Monthly SecOps). No CMMC, HIPAA, or PSA integration is mentioned. | [MKT] https://galacticsecurity.com/ ; [PRACT] https://community.syncromsp.com/t/galactic-scan/6689 |
| **Narmada** | Real vCIO/QBR platform. Its HaloPSA integration creates "tickets from issues discovered during a QBR or compliance audit" and shows client tickets. | [3P search snippet of halopsa.com integration page; page now redirects] https://halopsa.com/?p=4404 |
| **Blacksmith InfoSec** | Real. Multi-tenant CaaS with ConnectWise and HaloPSA (first pass). | [MKT] https://marketplace.connectwise.com/blacksmith-infosec |
| **GetCybr** | A vCISO/GRC platform is mentioned in a competitor's blog. Not examined. | [3P, competitor] https://fortifydata.com/blog/getcybr-competitors-and-alternatives/ |

---

## 2. PSA / RMM / M365 integrations

### 2.1 Who integrates with what (documented)
| GRC tool | HaloPSA | NinjaOne | ConnectWise | Autotask | Datto RMM | N-able | IT Glue | M365 / Entra / Intune |
|---|---|---|---|---|---|---|---|---|
| **ControlMap** | Indirect, through ScalePad hub ("over 20 PSA and RMM systems") [HELP]. ScalePad Lifecycle Manager pulls HaloPSA "contract costs, renewal dates, and hardware asset details" [MKT] | **Yes**, through ScalePad: inventory, AV, warranty. "Antivirus and Warranty data is currently populated only when the PSA/RMM source is Datto RMM, Kaseya VSA, or NinjaOne" [HELP] | Through ScalePad; Lifecycle Manager action items become CW Manage tickets [MKT] | Listed as an evidence source (2023) [HELP] | Yes, via ScalePad [HELP] | Lifecycle Manager syncs N-central/N-sight assets and software [MKT] | not found | O365 connector (users, MFA, needs P1/P2); Intune (users, MFA, devices, owners); GCC connector [HELP] |
| **Compliance Scorecard** | **Not found** | **Yes**: asset lists, OAuth client app, "Scopes: Monitoring," "Client Credentials and Refresh Token" [HELP] | Yes: client import, API keys, "Inquire" role [HELP] | Reseller claim only [3P] | Yes: "hardware, software, and human assets" [HELP] | N-central [HELP] | not found (Hudu yes) | MS Graph devices asset lists with draft → review → publish [HELP] |
| **Kaseya CM GRC** | not found | not found | not found | **POA&M issues → Autotask tickets** [HELP] | Compliance Monitor agent deployment [HELP] | not found | **Attach IT Glue docs to assessment questions/worksheets**; import IT Glue orgs [HELP] | Microsoft Cloud Assessment (MCAM) in TOC [HELP] |
| **Cynomi** | **Named on integrations page** (PSA). Data scope undocumented [MKT] | not found | Named (PSA) [MKT] | not found | not found | not found | not found | Microsoft Secure Score, Cloud Security Benchmark [MKT] |
| **Apptega** | not named; "your PSA" two-way task sync [MKT] | not found | logo only [MKT] | not found | not found | not found | not found | Azure AD logo [MKT] |
| **Drata** | — | **MDM connection (March 2026)**: FDE and screen lock via **custom fields + scripts** the customer installs; computers only [HELP] | — | — | — | — | — | Intune ("only one active Intune connection") [HELP] |
| **Vanta** | — | Device detail into Vanta [MKT] | — | — | — | — | — | — |

Sources:
- ControlMap: https://help.controlmap.io/hc/en-us/articles/19456371075739-About-the-PSA-RMM-Using-ScalePad-integration ; https://help.controlmap.io/hc/en-us/articles/18171156540443-Office-365-Connector ; https://help.controlmap.io/hc/en-us/articles/18171738917147-Connecting-to-Intune ; https://www.scalepad.com/lifecycle-manager/integrations/halopsa/
- Compliance Scorecard: https://compliancerisk.atlassian.net/wiki/spaces/CRIODOCS/pages/264962062/NinjaOne+API ; https://compliancerisk.atlassian.net/wiki/spaces/CRIODOCS/pages/265027632/ConnectWise ; https://compliancerisk.atlassian.net/wiki/spaces/CRIODOCS/pages/844627969/Datto+RMM ; https://compliancerisk.atlassian.net/wiki/spaces/CRIODOCS/pages/276267044/N-Able+N-Central ; https://compliancerisk.atlassian.net/wiki/spaces/CRIODOCS/pages/271155303/MS+Graph+API
- Kaseya: https://www2.rapidfiretools.com/cm-grc/help/cm-grc-docs/export-poam-tickets.htm ; https://www2.rapidfiretools.com/cm-grc/help/cm-grc-docs/cm-grc-itglue-worksheet-integ.htm
- Drata: https://help.drata.com/en/articles/13554422-ninjaone-integration-guide ; https://help.drata.com/en/articles/5604949-microsoft-intune-integration-guide-windows
- Vanta: https://www.vanta.com/resources/vanta-ninjaone-integration
- Cynomi: https://cynomi.com/platform/integrations/
- Apptega: https://www.apptega.com/platform/integrations

### 2.2 What the data is used for (the pattern)
1. **Client roster import.** PSA companies become GRC clients (Compliance Scorecard ConnectWise import; ControlMap prospect tenants created from the PSA/RMM). This is **exactly Johnathan's "pre-fill client profile"** need.
2. **Asset inventory as evidence.** RMM devices become an asset list that is versioned and re-synced on a schedule. Compliance Scorecard routes Graph imports through **"Edit Section Content → Submit for Review → publish."** ControlMap keeps per-scan history and a "Historical Asset Count" chart. [HELP] https://help.controlmap.io/hc/en-us/articles/53417600004891-GovCloud-Integrating-with-ScalePad-Lifecycle-Manager
3. **Automated pass/fail checks**, not answers. ControlMap: "Assets have active and up-to-date antivirus," "maintain an asset inventory," valid warranty. Intune: "All user accounts… assigned an owner," "admins have MFA enabled." Drata: FDE and screen lock. **No vendor documents RMM data auto-answering an assessment question.** The only auto-answer mechanism found is ControlMap Tech Stacks (MSP-declared tools pre-answer questions "with a review step") from the first pass.
4. **Push-out.** Findings and POA&M go out as PSA tickets: Kaseya → Autotask, Lifecycle Manager → CW Manage, Cynomi → "any PSA," Narmada → HaloPSA.
5. **Evidence attachments from documentation tools** (Kaseya ← IT Glue).

Caution: **ControlMap's ScalePad integration does not work on GovCloud.** That matters for CMMC MSPs who host GRC in GovCloud. [HELP, PSA/RMM link]

### 2.3 HaloPSA and NinjaOne APIs: usable from a local Windows desktop app?

**HaloPSA** [API] (Swagger v2, "The HaloITSM, HaloPSA and HaloCRM REST API", docs version 2.250.32) https://halo.halopsa.com/api/swagger/v2/swagger.json and https://halopsa.com/apidoc/
- **Auth:** OAuth2 bearer. You create an "API Application" in Configuration > Integrations > Halo API. "Client ID and Secret" is the most common method, and **"you do also need to select an Agent to impersonate"**. Permissions are the intersection of application permissions and agent permissions. A static API key exists but is discouraged. Postman examples are downloadable. [HELP] https://usehalo.com/halopsa/guides/1737/ Community code shows `POST {auth}/auth/token` with `grant_type=client_credentials&scope=all` [3P code] https://glama.ai/mcp/servers/@Switchboard666/halopsa-mcp/blob/8b239f0a87c4f99563b41d9621c42555050f5844/dist/halopsa-client.js
- **Endpoints relevant to RainTech** (paths from the spec):
  - `/Client`, `/Site`, `/Users` (end users / contacts), `/Agent`
  - `/Asset` (filters include `client_id`, `assettype`, `lastupdatefromdate`, `integration_type`), `/AssetSoftware` ("List of DeviceApplications", filter by `device_id`), `/Asset/GetAllSoftwareVersions`, `/AssetChange`, `/SoftwareLicence`
  - `/Tickets`, `/Actions`, `/Appointment`, `/Projects`, `/ClientContract`, `/RecurringInvoice`, `/KBArticle`, `/Report`
  - Integration mirrors: `/IntegrationData/Get/NinjaRMM`, `/IntegrationData/Get/Intune`, `/IntegrationData/Get/AzureAD`, `/IntegrationData/Get/Datto`
- **Patch status is not a first-class Halo resource.** It lives in the RMM. Halo holds what the RMM integration syncs onto assets; the field-level content was not verified.
- **Desktop suitability:** yes. Plain HTTPS + bearer token, client-credentials, no inbound callback needed. The secret must be stored locally (Windows DPAPI / Credential Manager). The impersonated agent should be a least-privilege, read-only agent.

**NinjaOne** [API] (OpenAPI "NinjaOne Public API 2.0", 2.0.9-draft) https://app.ninjarmm.com/apidocs/NinjaRMM-API-v2.json
- **Auth:** OAuth2 bearer. Scopes are **Monitoring** (read-only), Management, and Control.
  - NinjaOne's own setup page lists only Authorization Code, Refresh Token, and Implicit grants on Native / Single Page / Web platforms. [HELP] https://www.ninjaone.com/docs/integrations/how-to-set-up-api-oauth-token/
  - **But** Compliance Scorecard's current doc instructs "Allowed Grant Types: Client Credentials and Refresh Token" on a Web client app with Monitoring scope. Drata uses an OAuth redirect. [HELP, links above]
  - **Conflict noted:** client-credentials appears to work in practice, but NinjaOne's page does not say so. Regional hosts (app./eu./etc.) must be selected.
- **Endpoints relevant to RainTech:**
  - `/v2/organizations(-detailed)`, `/v2/organization/{id}/devices`, `/v2/devices-detailed`, `/v2/organization/{id}/end-users`, `/v2/contacts`
  - `/v2/device/{id}/software` and `/v2/queries/software` (**installed software inventory**: the CMMC monthly software-inventory check)
  - `/v2/queries/os-patches` ("Pending, Failed and Rejected OS patches"), `/v2/queries/os-patch-installs`, `/v2/queries/software-patches`
  - `/v2/queries/antivirus-status`, `/v2/queries/operating-systems`, `/v2/queries/logged-on-users`, `/v2/queries/device-health`, `/v2/backup/jobs`
  - `/v2/ticketing/ticket/{id}`, `/v2/organization/documents`, `/v2/organization/checklists`
- **Desktop suitability:** yes for read-only Monitoring scope. An authorization-code flow with a `localhost` redirect is the documented path for an interactive desktop app. Client credentials avoids the browser hop if the tenant offers it. Tokens expire in about 1 hour [3P] https://nango.dev/docs/integrations/all/ninjaone-rmm/connect

**Microsoft 365 / Intune:** Graph `GET /deviceManagement/managedDevices` returns `complianceState`, `isEncrypted`, `osVersion`, `lastSyncDateTime`, and `userPrincipalName` with `DeviceManagementManagedDevices.Read.All`, delegated or application. It is available in US Gov L4/L5 clouds. [API] https://learn.microsoft.com/en-us/graph/api/intune-devices-manageddevice-list?view=graph-rest-1.0 Desktop apps are "public client applications" using interactive, WAM, or device-code flows via MSAL. [HELP] https://learn.microsoft.com/en-us/entra/identity-platform/scenario-desktop-app-configuration

**CMMC caution for V2.** RMM and PSA tools that administer a CMMC client are Security Protection Assets and in assessment scope (32 CFR 170.19; see `docs/research/2026-10-competitor-ux/cmmc-tools.md` line 31–33). A practitioner source stresses that the trigger is Security Protection Data such as config, logs, and credentials [3P / practitioner] https://securecontrolsframework.com/grc-fundamentals/emerging-trends/msp-mssp-dumpster-fire. **Not independently verified beyond the search summary.** A RainTech desktop app holding NinjaOne or Halo credentials and pulled device, user, and patch data for a CMMC client would plausibly become part of Johnathan's own ESP footprint. That deserves an ADR before V2 work. It is not CUI, but it is security-relevant data.

---

## 3. What practitioners say makes CaaS work or fail
No r/msp threads could be retrieved (see access limits). What follows is vendor-hosted practitioner content and practitioner-written pieces, labeled accordingly.

- **Documentation drift is the top failure.** A C3PAO-side speaker ("Kyle") in a ScalePad webinar recap: "You want to make sure whatever you do matches what you documented." Also: "Do a practice test before the actual certification assessment," and "Make sure you have the scope and boundaries defined." The same list calls out outdated asset inventory, missing baselines, OPoA vs POA&M confusion, unclear inheritance, and missing provider evidence. [PRACT via MKT blog] https://www.scalepad.com/blog/11-common-cmmc-2-0-mistakes-msps-make-and-how-to-avoid-them **This directly supports the monthly policies/procedures/software-inventory focus and the yearly mock assessment.**
- **A responsibility matrix is not optional.** Without one, gaps between "what you think the MSP does and what the MSP thinks you do" become NOT MET. A generic service description is not a CRM. [3P practitioner articles, via search summary] https://www.deepfathom.ai/articles/shared-responsibility-cmmc ; https://scopable.io/blog/msp-compliance-pricing-guide
- **Reporting is the retention lever, framed as business outcomes.** "The purpose of reporting is to have a business strategy discussion that happens to be about security." Reports double as a due-diligence record "in… client disputes." It fails when it is "disconnected spreadsheets and manual compilation" or "lists activities instead of supporting strategic decisions." [3P, Cynomi-sponsored] https://thehackernews.com/2025/01/taking-pain-out-of-cybersecurity.html
- **Packaging:** setup fee plus a fixed monthly retainer is the common structure. Scope by framework count and size. Hourly work only for out-of-scope requests. Vendor ranges: HIPAA retainer $2,500–8,000/month and CMMC L2 $5,000–15,000/month (Scopable, a vendor blog); vCISO $1,000–5,000/month by tier (Cynomi). Treat all figures as vendor claims. [MKT] https://scopable.io/blog/msp-compliance-pricing-guide ; Cynomi link in 1.3
- **Annual reassessment is repetitive.** "MSPs told us that refreshing assessments each year was repetitive and time-consuming," which drove ControlMap Snapshots (first pass). [HELP]
- **Accountability rhythms work for the MSP too.** Compliance Scorecard sells weekly peer "accountability calls." Galactic runs a "Weekly Power Hour / Monthly SecOps." Both suggest that solo practitioners value a cadence and a regulatory-news feed. [HELP / MKT, links above]
- **Vendor demand claim:** "~70% of clients want compliance support, ~15% of MSPs offer it." [MKT, Kaseya webinar; unverified] https://webinar.kaseya.com/webinar-compliance-manager-grc/compliance-as-a-service-the-msp-revenue-stream-clients-cant-opt-out-of

---

## 4. Verdicts on the proposed redesign features

| Proposed feature | Verdict | Basis |
|---|---|---|
| **Home queue across clients** (overdue / next up / waiting on client) | **VALIDATED (cross-client overview); PARTLY (queue framing)** | Every MSP tool has a cross-client view: Compliance Scorecard dashboard with "pending tasks" across clients, ControlMap MSP dashboard and ToDo Kanban, Kaseya multi-sites status, Drata MIM. They are mostly **status boards or widgets, not a single prioritized queue.** ControlMap's weekly reminder email "across your environment" is the closest to "what's due." "Waiting on client" is backed by assignable items (ControlMap evidence requests with assignee; Compliance Scorecard "Open Entire Assessment to Client") but is not shown as its own lane anywhere found. |
| **12-month service-year strip, one monthly focus** | **NOVEL (as presented); PARTLY (underlying mechanics)** | No tool shows a per-client 12-month strip. Nearby: Lifecycle Manager roadmaps scheduled by **year + quarter**. Compliance Scorecard **project templates** ("annual audit preparation project") with milestones. Apptega and Hyperproof **recurring tasks** (monthly, "last Thursday of every month"). Build it from recurring tasks plus templates; the strip is the view. |
| **Monthly meeting record → focus points become tracked items → client summary** | **PARTLY (validated in vCIO tools, absent in GRC tools)** | Lifecycle Manager client strategy dashboard: "log meeting notes" + "publish Action Items" → PSA tickets. Narmada: QBR/audit issues → HaloPSA tickets. ControlMap only links action items to LM initiatives. No GRC tool found has a meeting object. Client summaries exist as Compliance Scorecard AI "Executive Summary," Cynomi branded progress reports, and Apptega **scheduled emailed reports**. Combining meeting + compliance items + summary in one tool is RainTech's own contribution. |
| **Regulatory change log tagged to frameworks, shows affected clients, records when each was told** | **NOVEL in MSP/vCISO tooling** | Vendors update framework content and announce it in release notes or community posts (ControlMap, Apptega, Hyperproof's HIPAA +173 requirements). Compliance Scorecard sells education calls. **No tool found tracks which clients a change affects or when each was told.** Enterprise GRC sells "regulatory change management," but the Resolver page could not be read (403). Not contradicted. Consistent with the "due-diligence record" argument in Cynomi's reporting guide. |
| **Multi-year client record with yearly assessment carry-forward** | **VALIDATED** | ControlMap Snapshots ("Keep all answers," prior answer shown), Kaseya "Use Previous Response" + **Archive Assessments**, Compliance Scorecard versioned assessment events (v1.0…), ControlMap "Refresh Evidence" keeps history. |
| **Recurring reviews and evidence staleness warnings** | **VALIDATED (strongly)** | Hyperproof freshness (Fresh → Expired, two expiry modes, dashboard widgets). ControlMap review date auto-flips Approved → **In Review**. ControlMap evidence "overdue" when undated. Apptega recurrence with a 1-week reminder. Drata recurring custom tasks. Compliance Scorecard's 4th "A" (review date set). |
| **V2: PSA/RMM pre-fill of profile and much of the gap analysis** | **PARTLY: profile and inventory pre-fill VALIDATED; gap-analysis auto-answers CONTRADICTED as stated** | Client roster import, asset and software inventory, AV, MFA, and encryption checks are common. **No tool documents RMM data answering assessment questions directly.** RMM data becomes evidence or pass/fail checks, and auto-answers come only from MSP-declared tech stacks with a review step. The existing "suggested vs confirmed" seam is the right model. Frame V2 as "pre-filled evidence and suggested answers," not "pre-filled gap analysis." |

### Things proven tools do that the proposal misses
1. **Push-out of work to the PSA.** POA&M and action items become Halo tickets (Kaseya → Autotask, Lifecycle Manager → CW Manage, Narmada → HaloPSA, Cynomi PSA sync). If Johnathan runs his business in Halo, V2 should consider **writing** focus items or POA&M lines as Halo tickets, not only reading from Halo.
2. **Shared-responsibility / RACI per control** (Compliance Scorecard MSP / company / shared + RACI; ControlMap SRM). Practitioners call this the most common CMMC failure for MSP-served clients.
3. **Reusable work templates across clients.** Compliance Scorecard "build once and deploy across clients," including CSV import. This is a natural source for the monthly-focus calendar ("CMMC maintenance year" template).
4. **Policy adoption and acknowledgment tracking** with e-signature and reminders (Compliance Scorecard; Kaseya Employee Portal). This is relevant to HIPAA workforce attestations even before a client portal (V3).
5. **Scheduled, recurring client reports** (Apptega report frequency + email; Compliance Scorecard Report History).
6. **Imported data goes through a review-and-publish step, with sync history** (Compliance Scorecard asset list draft → review → publish; ControlMap scan history and asset-count trend). This matches the "suggested vs confirmed" seam and adds **a dated history of each import**.
7. **Cost on POA&M lines** (Compliance Scorecard). Useful for the HIPAA yearly report and for upsell conversations.
8. **Archive or freeze a yearly snapshot** with its generated reports (Kaseya), distinct from carry-forward.

### Things to avoid
- Kaseya blocks archiving while "outstanding tasks" exist. Don't make the yearly close depend on a clean queue.
- Hyperproof stops recurrence if the template owner is deactivated. In a single-user app, recurrence must not depend on a user record.
- Drata's NinjaOne connection needs client-side **scripts and custom fields** for encryption and screen lock. Don't promise those fields from NinjaOne out of the box.

---

## 5. What could not be verified
- Any r/msp thread content (blocked or not surfaced).
- Cynomi: which data its HaloPSA and ConnectWise integrations carry, and whether it has a meeting or regulatory-update feature (no public help center).
- Compliance Scorecard + HaloPSA (none found). Its Autotask support (third-party reseller claim only).
- Vanta's MSP console UX and the exact NinjaOne fields it uses.
- Compliancy Group "Maintain" phase mechanics and Accountable partner pricing.
- NinjaOne client-credentials grant: contradicted by NinjaOne's own setup page, asserted by Compliance Scorecard's doc. Test on a real tenant.
- HaloPSA: how NinjaOne-synced fields (patch status, AV) appear on Halo assets. No live call was made against either API.
- Enterprise regulatory-change-management feature details (Resolver page 403).
- Exact 32 CFR 170.19 wording on ESP/SPA scope. It was not re-read this pass (eCFR blocked); the repo note was relied on.
