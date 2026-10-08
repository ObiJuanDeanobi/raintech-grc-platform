# Leading GRC / Compliance-Automation Platforms: UX Research

Research date: 2026-10-08. Track: interaction design of market-leading GRC tools, plus general enterprise UX guidance for dense data-entry tools.

Context: RainTech is a local-first, single-user Windows desktop app for a CMMC L2 / HIPAA assessor-consultant. The flow is client -> project -> profile -> assessment -> findings/POA&M -> evidence -> reports.

## How to read this

**Source labels**
- **[DOCS]**: vendor help center or product documentation. This is the strongest evidence of how the UI actually behaves.
- **[MKT]**: vendor marketing or blog posts.
- **[REVIEW]**: user reviews on G2, Capterra, or AWS Marketplace (which mirrors G2), or review aggregators.
- **[GUIDE]**: independent UX guidance (NN/g, Microsoft, GitHub Primer).

**Verification limits**
- **G2 and Capterra pages returned HTTP 403** to direct fetch. Review quotes marked "(via search snippet)" come from search-engine extracts of those pages. I could not open the full review to confirm them.
- **AWS Marketplace review pages did load.** Quotes taken from them were checked on the page.
- **Reddit:** two searches (r/grc, r/cybersecurity, r/sysadmin, r/SOC2 phrasing) returned **no usable Reddit threads**. There are no Reddit quotes in this document, and this gap remains open.
- **Hyperproof docs:** docs.hyperproof.io URLs now 301-redirect to `help.hyperproof.app/en/` (the root, not the matching page). Hyperproof details below come from search extracts of those doc pages. I did not fetch the pages themselves.
- **Not documented anywhere I found:** keyboard shortcuts or a command palette for Vanta, Drata, Hyperproof, or AuditBoard. A targeted search returned nothing ([search attempted; no vendor results]). Treat "no keyboard model" as likely but unconfirmed.
- **Product versions:** these products are web SaaS for multi-user companies, and Drata in particular now runs two UIs ("New Experience" vs "Classic"). Screens differ by plan and rollout.

---

## 1. Vanta

### Information architecture
- **Navigation:** a left sidebar with the most-used pages at the top: Home and Tests. Below them are Documents (policies and non-technical evidence), Reports, Compliance (frameworks), Manage (People, Computers, Access, Vendors, Inventory), and Settings/Integrations at the bottom. The 2022 redesign replaced a top nav because it "required the clicking of drop-downs to see what's nested beneath." [MKT] https://www.vanta.com/resources/vantas-new-look-a-customer-based-redesign
- **Why they redesigned:** customers asked for "clearer direction on what to do within Vanta on a day-by-day basis" and an at-a-glance view of progress. [MKT] same URL
- **Home page sections:** Compliance Progress (up to three frameworks in progress), Monitoring ("items needing attention across compliance and risk workloads", with a hover tooltip breaking open items down by category), and View Tasks (SLA-bound items outstanding or coming due). [DOCS] https://help.vanta.com/hc/en-us/articles/7238685176468-Home-Page
- **Priority tasks:** the redesign added this section to Home, framed around the question "What do I have to do today to remain compliant?" It can be filtered by standard and urgency, and "every component is clickable for more detail and action." [MKT] redesign URL above
- **My Work page:** "a single, centralized view of the work that needs your attention." [DOCS] https://help.vanta.com/en/articles/11997605-my-work-page
  - Groups: **Urgent** (overdue or needs remediation), **Coming soon**, **Unscheduled**, **Waiting on others**.
  - Quick filters: "Needs my approval", "Assigned to me", "Assigned to my teams".
  - It is the default landing page for Collaborator roles. Admins land on Home.
- **Onboarding:** a Compliance Roadmap, reachable from the profile icon, walks through setup. It hides itself three days after completion and can be re-opened. [DOCS] https://help.vanta.com/en/articles/11345375-getting-started-resources-in-vanta

### Controls screens
- **List contents:** the Controls page lists all controls. A summary strip at the top shows controls that still need owners and controls with passing evidence. [DOCS] https://help.vanta.com/hc/en-us/articles/11750680642196-Controls-Page
- **Search and filters:** search sits top-left. The Evidence column can be filtered to "no mapped evidence."
- **Custom fields:** these become new list columns. Each custom field has a "Share with auditor" toggle.
- **Editing:** clicking a control opens it to edit the summary and description, followed by an explicit **Save Changes**. The doc does not say whether this is a panel or a page. Tests, documents, frameworks, and risks are mapped from the same view.
- **Bulk actions documented:** only multi-select **Deactivate**. Remove uses a 3-dot menu and asks for an effective date.
- **Common controls tab:** a reporting layer that maps controls across frameworks.

### Status model
- **Two derived states:**
  - **Ok:** all mapped automated tests and documents pass.
  - **Needs evidence:** nothing is mapped, or something mapped is failing.
- You cannot set the status by hand. You change it by mapping passing evidence.
- "Control status is not visible to auditors." [DOCS] Controls Page URL above
- **Policy-to-control mapping** is done from the policy side (Mapped elements -> Map control), with "AI-suggested" controls offered. [DOCS] same
- **Policy lifecycle:** Draft -> Pending (sent for approval) -> Approved -> "Renew soon" (expiring within 6 weeks) -> "Needs remediation" (expired). Approval and employee acceptance are separate steps. [DOCS] https://help.vanta.com/hc/en-us/articles/360053538991-The-Policies-Page and https://help.vanta.com/en/articles/11345363-getting-started-with-policies
- **Tests:** can be deactivated (a reason is required, evidence is optional) or snoozed until a date, after which they re-enable automatically. A single resource can be muted from a test. [DOCS] https://help.vanta.com/en/articles/11345549-deactivate-a-test

### Audit and review workflow
- **Information Request List (IRL) statuses:** **Not ready -> Internal review -> Audit ready -> Flagged / Accepted.** The customer controls the first three. Only the auditor can set Flagged or Accepted. [DOCS] https://help.vanta.com/en/articles/12293647-information-request-list-irl-in-vanta
  - Accepted items lock: no evidence can be added until the auditor moves the item back to Flagged.
- **Bulk editing of requests:** due date, capture date, type, cadence, and owner, plus an "Assign Owner" toolbar action. Bulk import handles up to 2,000 requests from XLS/CSV. [DOCS] same
- **Two comment threads per request:** an internal one and an auditor-facing one, with @mentions. Notifications are batched over 30 minutes. [DOCS] same
- **Auditor actions:** Accept, Flag (a reason is required), or Mark not required, all from a right-hand detail view. [DOCS] https://help.vanta.com/en/articles/11346120-approve-or-flag-evidence-in-an-audit
- **After a flag:** the customer replies with updated evidence, a comment, and a "Request auditor review" checkbox, which returns the item to Ready for audit. (via search extract of Vanta help) https://help.vanta.com/en/articles/11345427-audit-evidence

---

## 2. Drata

### Information architecture
- **Dashboard:** "brings together readiness, alerts, trends, and tasks." [DOCS] https://help.drata.com/en/articles/13259515-dashboard-overview-new-experience
  - **Readiness overview:** one card per framework, showing % of controls ready, a progress bar, and remaining controls. Frameworks at 0% are hidden. Clicking a card opens Controls pre-filtered to that framework's in-scope controls.
  - **Notifications:** auditor messages and other time-sensitive items.
  - **Test trends:** failing tests and the change over 7 days.
  - **Policies status:** Active / Needs approval / Ready to publish / Renews soon / Past due.
  - **Vendor risk** donut, **Connections** errors, and **Personnel** non-compliant count.
  - **Tasks:** a Task Forecast plus a Task List of upcoming and overdue items.
- **Two UIs:** customers who joined on or after Feb 24, 2026 get the "New Experience". Older accounts use Classic. [DOCS] same

### Controls screens
- **New Experience:** a full control page with tabs: **Overview** (readiness cards for Evidence, Monitoring, Policies, Approvals, plus Info, Owners, and Required Approvals), **Evidence**, **Monitoring**, **Policies**, **Frameworks**, and **Risks**. Notes, tasks, and tickets are managed from the control too. [DOCS] https://help.drata.com/en/articles/13372784-assess-and-manage-individual-controls-new-experience
- **Classic Experience:** a **side drawer** with CONTROL INFO, MAPPED REQUIREMENTS, AUTOMATED TESTING, and CONTROL EVIDENCE. The drawer has expand/close and "mark out of scope" in the corner. [DOCS] same
- Note that Drata moved from a drawer to a full page in the New Experience. One reading is that control detail outgrew a drawer once it had six facets.
- **Bulk actions:** none documented for controls.

### Status model
- **Readiness is derived** from evidence, monitoring tests, policies, and approvals. [DOCS] control detail URL above
  - Examples that "do affect readiness": missing evidence, unpublished policies, pending approvals.
  - Inactive or erroring tests are excluded from the calculation.
  - There is no manual status override documented.
- **Control owners:** one or more per control. **Required Approvals** act as a lightweight sign-off, and a pending approval blocks readiness. [DOCS] same

### Tasks
- **Two kinds:** automated (policy renewals, control approvals, evidence reviews, vendor reviews) and custom (general, risk-mapped, or control-mapped). Custom tasks can recur. [DOCS] https://help.drata.com/en/articles/13688199-manage-tasks-in-drata-new-experience
- **Tasks page:** a monthly timeline grouped by month and type, filterable by owner, type, and timeframe. Missed due dates are flagged "Past due".
- **Completion:** a checkmark completes simple tasks. A **Review** button opens the related record, and finishing the action there completes the task. That second pattern is worth noting: the task closes itself when the real work is done.

### Audit
- **Audit Hub:** auditors post requests mapped to controls and evidence. Request statuses are New / Prepared / Completed. Only auditors can mark Completed. [DOCS] https://help.drata.com/en/articles/6928357-audit-hub (via search extract)
- Drata's marketing positions the Audit Hub as eliminating "endless emails, Slacks, and notifications requesting evidence". [MKT] https://drata.com/products/compliance/audit-hub

---

## 3. Secureframe

### Information architecture
- **Homepage, top:** three charts. [DOCS] https://support.secureframe.com/en/articles/15111099-homepage-charts-action-items-and-frameworks
  - **Testing:** % passing.
  - **Control Health:** Healthy / Unhealthy / At Risk / Not Tested.
  - **Vendor Health.**
- **Action Items:** a time-based list (test due dates, evidence expiry, vendor reviews, tasks). Each item shows name, event type, **owner**, and **due date**.
  - Caveat in the doc: failing or overdue tests without a due date do **not** appear in Action Items.
- **Framework progress:** "% of Tests passing" per active framework. Available frameworks show "the exact number of overlapping controls", which sells reuse.

### Controls screens
- **Controls page:** in the Monitoring view's left nav. [DOCS] https://support.secureframe.com/en/articles/15111090-using-the-controls-view-in-secureframe
- **Detail tabs:**
  - **Details:** ID, description, frameworks, tests, status, owner, implementation date and plan, maturity 1-5, tags.
  - **Requirements:** the framework requirement text.
  - **Testing:** tests with type, frequency, and status (Passing / Failing / Needs Review). You can upload evidence or run a test here.
  - **Comments:** timestamped, with author.
- **Bulk action:** checkbox multi-select, then **"Mark as N/A"** from a bottom action bar. A justification is required.

### Status model
- **Health is derived from mapped tests:** Healthy / At Risk / Unhealthy / **Draft**. Draft means not implemented, and clears once an implementation date is set.
- **Manual override with an audit trail:** "Edit control status" lets you choose a status with a **required justification**. **"Restore the original status"** reverts to the computed value. [DOCS] controls view URL above
- **Maturity 1-5:** a separate, optional rating, kept apart from health.
- This is the cleanest pattern found for "derived by default, assessor can override, with a reason, and can revert".

### Audit
- **AI Evidence Validation** (launched May 2025) checks uploaded evidence against the test criteria and the audit window before the auditor sees it. [MKT] https://secureframe.com/blog/announcing-ai-evidence-validation
- **Auditor workflow:** I found no step-by-step help article. **Unverified.**

---

## 4. Hyperproof

All Hyperproof material comes from search extracts of docs.hyperproof.io pages, which now redirect.

### Status model: the most explicit multi-dimension model found
- **Inputs:** control health is computed from five dimensions: **testing, implementation, freshness, proof count, and past-due issues.** [DOCS] https://docs.hyperproof.io/cm/en/getting-started/turning-on-program-health/control-health
- **Implementation states:** Unknown / Not started (default) / In progress / Completed.
- **Testing states:** Effective / Ineffective, derived from tests.
- **Freshness:** Fresh / Expired, using an expiration period set per control.
- **Health rules:**
  - **Critical** if testing is ineffective or implementation is not complete.
  - **At risk** if untested, if freshness is unknown or expired, if there is **zero proof**, or if any linked issue is past due.
  - **Healthy** only if all five pass.
- **Program health** rolls up requirement status and the health of linked controls. [DOCS] https://docs.hyperproof.io/cm/en/getting-started/turning-on-program-health/program-health
- **Needs Attention panel:** the program dashboard has one that watches for expired or soon-to-expire controls. [DOCS] (via search extract of https://docs.hyperproof.io/cm/en/best-practices/control-maintenance-best-practices)

### Evidence reuse
- **One proof item, many controls:** the same proof can link to multiple controls, and the **latest version** of the proof is what links. [DOCS] https://docs.hyperproof.io/cm/en/work-items/requests-overview/linking-request-proof-to-controls
- **Requests:** when proof arrives through a request, you choose whether it attaches to the linked controls, the linked labels, or both. [DOCS] same

### My work
- **Work items dashboard, "My work items" widget:** shows your items oldest-first. [DOCS] https://docs.hyperproof.io/cm/en/work-items/understanding-the-work-items-dashboard
  - A **Remind** badge marks past-due items.
  - A **Review** badge marks items you created that are now ready for you to review. That second badge is a light sign-off cue built into the queue.
- **Type tabs:** Tasks, Repeating tasks, Requests, and Evaluations, each with bulk edit.

---

## 5. Sprinto

- **Control Health Dashboard:** [DOCS] https://docs.sprinto.com/dashboard/control-health-dashboard
  - Headline is "the average readiness of all configured controls". Readiness rolls up from checks to controls to areas to the framework.
  - A trend chart covers 7, 15, or 30 days.
  - "Controls set up vs pending setup" tracks configuration progress.
- **Buckets per area:** controls fall into three buckets within each area (People, Policies, Risks, Trainings):
  - **Needs Setup:** no owner, checks, or framework link yet.
  - **Needs Work:** configured, but with failing or pending checks.
  - **100% Ready.**
  - This three-bucket split separates "not configured" from "configured but failing", which most tools blur together.
- **Personal queue:** a "Checks assigned to you" widget lists your pending items by severity. [DOCS] same
- **Monitoring table:** filters by framework, control, area, task status, **owner**, provider, and check type. Each row has a **"View & Fix"** action. [DOCS] https://docs.sprinto.com/monitoring/dashboard-actions/view-and-investigate-checks (via search extract)
- **Workflow checks:** manual checks become due, the assignee submits evidence, and the status updates. [DOCS] (via search extract) https://docs.sprinto.com/data-library/vulnerabilities/dashboard-actions/run-and-monitor-workflow-checks

---

## 6. Thoropass

- **Navigation (after a recent update):** Dashboard and Tasks sit in an overview group. Controls, Automated Evidence, and Audits sit under "Audit Lifecycle". Documents sit under Compliance Tools. [DOCS] https://help.thoropass.com/en/articles/14022302-thoropass-navigation-update (via search extract)
- **Dashboard:** summary cards for Monitors (violations), Integrations (errors), and Policies (unpublished reminders). [DOCS] https://help.thoropass.com/en/articles/8599619-what-is-on-the-dashboard-page (via search extract)
- **Differentiator:** the auditor is bundled, and the audit runs in-platform. Thoropass markets assigning tasks, tracking evidence requests, commenting, and messaging auditors "all in one platform". It also sells "First Pass AI", which flags missing or outdated evidence before submission. [MKT] https://thoropass.com/products/
- **Weakly sourced:** an aggregator says manual upload paths "can feel unclear until a project manager guides you", and notes UI clutter as monitor and evidence volume grows. [REVIEW, aggregator] https://www.rfp.wiki/it-security/software-development/devops-continuous-compliance-automation-tools/thoropass

---

## 7. AuditBoard (now branded Optro), light coverage

- **Ease of use vs Archer:** G2 shows an Ease of Use score of **8.8 for AuditBoard/Optro (~1,368 reviews) vs 6.8 for Archer (15 reviews)**. Reviewers call Archer "clunky" by comparison. [REVIEW, via search snippet] https://www.g2.com/compare/archer-technologies-archer-vs-optro
- **Review loop:** a Capterra reviewer said "the process of reviewing tester's work, pushing back comments, updating documents in real-time" saved time. [REVIEW, via search snippet] https://www.capterra.com/p/148230/SOXHUB/reviews/?page=8
- **Workpapers:** described as working the way audit methodology expects, with preparer and reviewer sign-offs and versioning. [third-party comparison] https://www.bdemerson.com/article/auditboard-vs-workiva
- **Gap:** I could not reach AuditBoard's own sign-off documentation. **Unverified** at the click level.

## 8. Others with notably praised UX
- A search for Scrut, Anecdotes, Oneleet, and Delve UX reviews returned nothing usable. **Unverified.**
- StandardFusion has Capterra reviews praising a "clean and intuitive interface". [REVIEW, via search snippet] https://www.capterra.com/p/151388/StandardFusion/reviews/
- I would not weight these.

---

## 9. Real user praise and complaints (short quotes)

**Vanta**
- "Vanta is very simple and intuitive to understand." (Sep 21 2026) [REVIEW, page fetched] https://aws.amazon.com/marketplace/reviews/reviews-list/prodview-5ophamrbfxt44?page=15
- "Vanta's sheer breadth of capabilities can sometimes be overwhelming and negatively impact the user experience." (Oct 2 2026) [REVIEW, page fetched] same URL
- "there are a few minor UI rough edges and workflow friction points." (Oct 1 2026) [REVIEW, page fetched] same URL
- "Vendor assessments don't make it easy to see which one is the old one and the new one." (Sep 21 2026) [REVIEW, page fetched] same URL. This one is a versioning-visibility complaint.
- The reviewer "wished the going-back-to-previous-page functionality could be improved", and must "return to the home page or module-specific page each time". [REVIEW, via search snippet] https://aws.amazon.com/marketplace/reviews/reviews-list/prodview-5ophamrbfxt44?page=189
- G2 review titled "Great product and service but confusing UX/UI" (3/5). [REVIEW, via search snippet] https://g2.com/products/vanta/reviews/vanta-review-7347211
- "the main dashboard lacks the ability to clearly determine what actions are required at the time of viewing", and "Vanta likes to open new browser windows and its easy to lose track of how you got a certain page." [comparison blog quoting reviews] https://www.complyjet.com/blog/vanta-vs-drata-2025

**Drata**
- "not always as intuitive as it could be. There are times when I am not sure where to find what I am looking for even after using the site off and on for over a year." [REVIEW, via search snippet] https://www.g2.com/survey_responses/drata-review-13225049
- "the pass/fail results could be easier to read for the monitors." [REVIEW, via search snippet] https://aws.amazon.com/marketplace/reviews/reviews-list/B09ZK1BZZP?page=26
- "sometimes it becomes challenging to review everything individually. A simpler, summarized view would make the experience even better." [REVIEW, via search snippet] https://g2.com/products/drata/reviews_and_filters?page=3
- Navigating from a control to a monitor is direct, "but returning means starting over from the category tab". Another reviewer asked for saved favorites. [REVIEW, via search snippet] https://aws.amazon.com/marketplace/reviews/reviews-list/B09ZK1BZZP?page=88
- "some of the controls can be a bit confusing if they are tied to several different tests." [REVIEW, via search snippet] same results set
- "clean, easy to navigate and most importantly, is intuitive." [REVIEW, via search snippet] https://g2.com/products/drata/reviews?page=4

**Secureframe**
- The G2 summary praises ease of use. Complaints focus on integrations (184 mentions) more than UI. One reviewer said "the personnel page can be a bit confusing". [REVIEW, via search snippet] https://g2.com/products/secureframe/reviews?page=2

**Hyperproof**
- G2 summary themes: "steep learning curve" (~17 reviews) and "not intuitive" (~13), against ~32 praising the interface. [REVIEW, via search snippet] https://g2.com/products/hyperproof/reviews_and_filters?page=4
- "too many manual steps required for routine tasks." [REVIEW, via search snippet] https://www.g2.com/products/hyperproof/reviews/hyperproof-review-11226972

**Sprinto**
- "dashboard is easy to navigate and shows all necessary information on one page." [REVIEW, via search snippet] https://aws.amazon.com/marketplace/reviews/reviews-list/prodview-ixyb464cbjkam?page=96

**Thoropass**
- "between their customer support and online portal, our evidence collection process and engagement with our auditor was stress free." [REVIEW, via search snippet] https://www.g2.com/survey_responses/thoropass-review-7478460

**Cross-cutting theme from the complaints**

| Complaint | Examples above |
|---|---|
| Losing your place: no good back, new windows, drill-down then start over | Vanta, Drata |
| Too many capabilities at once | Vanta, Hyperproof |
| Unclear "what do I do now" | Vanta |
| Item-by-item review with no summary | Drata |
| Confusing many-to-many control/test mappings | Drata |
| Old vs new version not visible | Vanta |

---

## 10. General enterprise UX guidance for dense data-entry tools

### Complex applications
- **Source:** "8 Design Guidelines for Complex Applications", Kaplan, Nov 2020. [GUIDE] https://www.nngroup.com/articles/complex-application-design/
- **Flexible pathways:** "avoiding rigid, linear workflows". Users skip steps and come back. This matters for an assessment where objectives are answered out of order.
- **Track actions and thought processes:** "keep a record of their actions and thought processes" so users can resume after interruption. Assessors are interrupted constantly.
- **Secondary information:** "access and view supplemental information without leaving the primary screen". This argues for inline panels over navigating away.
- **Clutter:** "minimizing the appearance of clutter … without reducing the capability".
- **Salience:** "Removing nonessential elements can be equally or even more effective" than adding emphasis.

### Master-detail / list-details
- **Pattern:** Microsoft's Windows guidance describes a list pane plus a details pane that updates on selection. Use **side-by-side at 641 epx or wider** and stacked when narrow. It suits "locate and prioritize a large collection of content" and "working back-and-forth between contexts". [GUIDE] https://learn.microsoft.com/en-us/windows/apps/design/controls/list-details
- **Always an active item:** Azure DevOps guidance says the collection list should "always have one active item". [GUIDE] https://developer.microsoft.com/en-ca/azure-devops/components/master-detail
- **Coverage gap:** I found no NN/g article specifically on master-detail.

### Data tables
- **Source:** "Data Tables: Four Major User Tasks", Laubheimer, Apr 2022. [GUIDE] https://www.nngroup.com/articles/data-tables/
- **Filters:** should be "discoverable, quick, and powerful", with a clear indication when a filter is active.
- **Inline edit:** works "only if the table is narrow". The row being edited must look different.
- **Row actions:** inline buttons work for "one or two actions". More than that gets crowded or hidden.
- **Bulk actions:** checkboxes plus an action bar, with Select All.
- **Frozen headers:** freeze header rows and columns.
- **Expanding rows:** users "don't tend to clean up after themselves", and expanding makes non-adjacent rows hard to compare.

### Progressive disclosure
- **Source:** Nielsen, Dec 2006. [GUIDE] https://www.nngroup.com/articles/progressive-disclosure/
- **What goes first:** frequent features go on the initial display, and the control that reveals more must set "clear expectations".
- **Depth:** limit disclosure to **two levels**. Users get lost beyond that.
- **Staged disclosure (wizards):** works when steps "have little interaction". It is problematic when steps are interdependent.

### Modal vs nonmodal
- **Source:** Fessenden, Apr 2017. [GUIDE] https://www.nngroup.com/articles/modal-nonmodal-dialog/
- **When modals are right:** irreversible or critical warnings, and required input that blocks a process.
- **When to avoid them:** when the user needs to see the content the modal hides.
- **Bottom line:** "no one likes to be interrupted, but if you must, make sure it's worth the cost."
- **Implication:** editing a control or objective should happen in a nonmodal detail pane, not a modal.

### Autosave vs explicit save
- **NN/g:** no dedicated NN/g article found.
- **GitHub Primer:** [GUIDE] https://primer.style/ui-patterns/saving
  - "When designing a form, start with an explicit saving pattern."
  - Use automatic saving "when the user expects instant feedback", for example toggles and single-select status controls.
  - On failure, preserve the user's data and show feedback.
  - **"never mix save patterns in a single form"**.
- **Grafana:** use explicit save when editing entities in rows. [GUIDE] https://grafana.com/developers/saga/patterns/save/
- **Make autosave visible:** "silent autosave is a trust trap", so show a saved-state indicator. [GUIDE, blog] https://www.saasui.design/blog/saas-autosave-save-states-ux-patterns
- **NN/g on system status:** "Whenever users interact with a system, they need to know whether the interaction was successful." [GUIDE] https://www.nngroup.com/articles/visibility-system-status/

### Keyboard accelerators
- **Source:** NN/g Heuristic #7, Laubheimer, Nov 2020. [GUIDE] https://www.nngroup.com/articles/flexibility-efficiency-heuristic/
- **Discoverability:** "The trick for designing a usable accelerator is making it discoverable." Show shortcuts next to their commands.
- **Customization:** "most users won't bother to customize the system". Don't rely on customization for efficiency.
- **Lightweight personalization:** remember the user's last sort order and similar settings across sessions.

### Empty states
- **Source:** Kaplan, Sep 2021. [GUIDE] https://nngroup.com/articles/empty-state-interface-design
- **Three guidelines:**
  - Communicate system status. "Totally empty states cause confusion about how and whether the system is working."
  - Provide learning cues.
  - "Provide direct pathways for getting started with key tasks."

### Onboarding
- **Tutorials don't help:** NN/g's tutorial study (70 users, 4 apps) found deck-of-cards tutorials did not improve success and made tasks *feel* harder. It recommends contextual help instead. [GUIDE] https://www.nngroup.com/articles/mobile-tutorials/
- **Checklists:** I found no NN/g article specifically on onboarding checklists. Vendor sources favor checklists that users complete while doing real work. [vendor blog, weak] https://supademo.com/blog/in-app-onboarding
- **Vanta's Roadmap:** a working example of a dismissible, re-openable checklist. [DOCS] https://help.vanta.com/en/articles/11345375-getting-started-resources-in-vanta

### Dashboards
- **Source:** Laubheimer, Jun 2017. [GUIDE] https://www.nngroup.com/articles/dashboards-preattentive/
- **Purpose:** "at-a-glance information", and the "goal is not to facilitate exploration".
- **Encoding:** use length and position (bars) rather than pies, donuts, or gauges. Don't use color for magnitude.
- **Implication:** framework/family readiness should be horizontal bars, not donuts. Several vendors use donuts anyway (for example, Drata's vendor risk widget).

---

## Patterns worth copying

1. **Home answers "what do I do today."** Vanta's redesign happened because users wanted "clearer direction on what to do … day-by-day". For RainTech, the home screen should be a ranked work queue for the open engagement, not a menu of modules. Vanta's grouping translates directly: Urgent/overdue, Coming soon, Unscheduled, Waiting on others (the last one is "waiting on client").
2. **Progress cards drill into a pre-filtered list.** In Drata, clicking a framework readiness card opens Controls filtered to that framework. Every number on the dashboard should be a link to exactly the rows behind it, for example "AC family: 14/22 met" opening those 22 objectives filtered.
3. **Derived status, plus override with a justification, plus "restore calculated".** Secureframe's model fits an assessor well. The system proposes a status from evidence and objective answers. The assessor can override it with a required reason, and can revert. This keeps the human in charge and leaves an audit trail.
4. **Separate "not set up" from "set up but failing".** Sprinto's Needs Setup / Needs Work / 100% Ready buckets. For CMMC this maps to Not assessed / Assessed: gaps (NOT MET -> POA&M) / MET.
5. **Make the dimensions of health explicit.** Hyperproof breaks health into implementation, testing, freshness, proof count, and issues. A RainTech objective could show small, independent chips: Determination (Met/Not Met/N/A), Evidence (count), Evidence freshness, Open POA&M item.
6. **Evidence is reusable, one-to-many, and versioned.** Hyperproof links one proof item to many controls and always links the latest version. One artifact (for example, the SSP or an access-control policy) should satisfy many objectives, attached once. Old vs new versions must be obvious, which was a direct Vanta complaint.
7. **Tasks close themselves when the real work is done.** Drata's "Review" button opens the record, and the task completes when the underlying action does. This avoids a separate, duplicate "mark task done" step.
8. **Review is a status lane, not a separate module.** The Vanta IRL flow (Not ready -> Internal review -> Ready -> Flagged/Accepted) keeps internal comments and client-facing comments apart. For a single-user assessor, a light "Draft -> Reviewed" toggle per objective, plus an internal notes field separate from report text, gives sign-off without ceremony. Hyperproof's "Review" badge in the queue is a good cue.
9. **Bulk actions with a required reason where it matters.** Secureframe's checkbox, then "Mark as N/A", then justification. Vanta's bulk owner and due-date edits. Assessors need bulk N/A for inherited or out-of-scope objectives, and bulk-apply evidence.
10. **Snooze or defer with an auto-return date.** Vanta's "Snooze monitoring" re-enables on a date. This maps to "revisit this finding on <date>".
11. **Dismissible, re-openable setup checklist.** Vanta's Compliance Roadmap hides after completion but can be re-opened. Use it for first-run: create client, then project, then profile, then start assessment.
12. **Side-by-side master-detail for objectives.** Microsoft's Windows list/details pattern and NN/g's "supplemental information without leaving the primary screen". Drata Classic's drawer is the web equivalent. A desktop app has the width to keep the list visible, with the selected objective editable on the right and always one active item.
13. **Keyboard-driven review is open ground.** No leading vendor documents shortcuts. For a desktop power tool: J/K or arrows to move through objectives, number keys for Met/Not Met/N/A, Ctrl+Enter to save and advance, and a Ctrl+K command palette, with shortcuts shown beside their commands (NN/g heuristic #7).

## Patterns to avoid

1. **Module sprawl as top-level navigation.** Vanta's and Hyperproof's top complaints are breadth ("sheer breadth … overwhelming", "steep learning curve"). RainTech's top level should follow the engagement spine (Client -> Project -> Assessment), not one sidebar entry per data object.
2. **Navigation that loses your place.** Reviewers complain about no working back, new browser windows, and drill-down followed by "starting over from the category tab". In a desktop app: no new windows for detail, a real Back, breadcrumbs, and list scroll, filter, and selection preserved when returning.
3. **Item-by-item review with no summary.** Drata: "challenging to review everything individually". Provide a summary or rollup row per family and a "next unreviewed" action.
4. **Opaque many-to-many mapping.** Drata: controls "tied to several different tests" are confusing. When evidence maps to many objectives, show the reverse links ("used by 7 objectives") inline.
5. **Status the user can't influence or understand.** Vanta's controls have only two states, derived and not settable. That works for SaaS automation, but is wrong for an assessor whose determination *is* the product. Never let a computed status silently disagree with the assessor's call.
6. **Action lists with blind spots.** Secureframe's Action Items omit failing or overdue items that have no due date. The "what next" queue must include every open item, with unscheduled items shown as a group (as in Vanta's My Work).
7. **Dashboards of donuts and gauges.** NN/g advises bars and position over area and angle. Avoid decorative charts that don't link to work.
8. **Modal editing and mixed save models.** Don't edit objectives in modal dialogs (NN/g). Don't mix autosave and Save on one form (Primer). For RainTech, pick one: either autosave with a visible "Saved" state, or explicit save per record. Given the local-first and versioning requirements, autosave with a visible state and per-field undo is likely the smoother choice. That is a judgment call, not a sourced fact.
9. **Front-loaded tutorials.** NN/g found tutorials don't improve task success. Prefer empty states that explain and offer the next action ("No evidence yet. Attach a file or link existing evidence.").
10. **Hiding the readiness math.** Drata reviewers asked for clarity on "what is required for control readiness" (via comparison blog https://www.brightdefense.com/resources/drata-vs-vanta-a-comparison/). Every percentage should explain itself on hover or click (for example, "73% = 80 MET of 110").
