// Capture #145 evidence screenshots against running apps (synthetic data only).
//
// Serve two apps and seed each with seed_synthetic_projects.py (see that file):
//   READY=http://127.0.0.1:18460/  an ordinary app
//   FAILING=http://127.0.0.1:18461/ the app started with serve_with_failing_backup.py
// Usage: PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers READY=... FAILING=... \
//   node docs/evidence/issue-145/capture_screenshots.mjs <out-dir> <draft-csv-dir>
//
// The DOCX and XLSX draft pages are rendered from the downloaded drafts with LibreOffice
// and pdftoppm (see VERIFICATION.md); <draft-csv-dir> holds the unzipped CMMC draft.
import { readFileSync } from "node:fs";

import { chromium } from "/opt/node22/lib/node_modules/playwright/index.mjs";

const [out, csvDir] = process.argv.slice(2);
const browser = await chromium.launch();
const results = {};

async function open(base) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await page.goto(base);
  await page.waitForSelector(".topbar nav");
  return page;
}

async function pickProject(page, name) {
  const select = page.locator(".project-switcher select");
  const option = select.locator("option", { hasText: name });
  await select.selectOption(await option.getAttribute("value"));
  await page.waitForTimeout(1200);
}

async function openReady(base) {
  const page = await open(base);
  await pickProject(page, "HIPAA 2026 (ready to issue)");
  return page;
}

async function reports(page) {
  await page.getByRole("button", { name: "Reports", exact: true }).first().click();
  await page.waitForSelector(".reports-actions");
}

// 1. The ready project: the Reports tab and the dialog with warnings.
{
  const page = await openReady(process.env.READY);
  await reports(page);
  await page.screenshot({ path: `${out}/05-reports-tab-draft-and-issue-1440.png` });
  await page.getByRole("button", { name: "Review and issue…" }).click();
  await page.waitForSelector(".review-issue-dialog .issue-worth-checking");
  await page.waitForTimeout(300);
  results.dialog_with_warnings = {
    must_fix_section: await page.locator(".issue-must-fix").count(),
    warnings: (await page.locator(".issue-worth-checking li strong").allInnerTexts()),
    checkboxes_in_dialog: await page.locator(".review-issue-dialog input[type=checkbox]").count(),
    reviewer: (await page.locator(".issue-who dd").first().innerText()),
    issue_enabled: await page.getByRole("button", { name: "Issue", exact: true }).isEnabled(),
  };
  await page.screenshot({ path: `${out}/06-review-and-issue-dialog-with-warnings-1440.png` });
  await page.getByRole("button", { name: "Cancel" }).click();

  // 2. A project with work left: the hard gates, each linking to its list.
  await pickProject(page, "HIPAA 2026 (draft only)");
  await reports(page);
  await page.getByRole("button", { name: "Review and issue…" }).click();
  await page.waitForSelector(".review-issue-dialog .issue-must-fix");
  await page.waitForTimeout(300);
  results.dialog_with_hard_gates = {
    groups: await page.locator(".issue-must-fix li button").allInnerTexts(),
    issue_enabled: await page.getByRole("button", { name: "Issue", exact: true }).isEnabled(),
  };
  await page.screenshot({ path: `${out}/07-review-and-issue-dialog-must-fix-1440.png` });
  await page.getByRole("button", { name: "Cancel" }).click();

  // 2b. A Profile approved while it still records an unknown: a hard gate, with a link.
  await pickProject(page, "HIPAA 2026 (unknowns)");
  await reports(page);
  await page.getByRole("button", { name: "Review and issue…" }).click();
  await page.waitForSelector(".review-issue-dialog .issue-must-fix");
  results.dialog_with_profile_unknowns = {
    groups: await page.locator(".issue-must-fix li button").allInnerTexts(),
    issue_enabled: await page.getByRole("button", { name: "Issue", exact: true }).isEnabled(),
  };
  await page.screenshot({ path: `${out}/12-profile-unknowns-block-issue-1440.png` });
  await page.getByRole("button", { name: "Cancel" }).click();
  await pickProject(page, "HIPAA 2026 (draft only)");

  // 3. The Profile: one Approve version button, no separate review step.
  await page.getByRole("button", { name: "Profile", exact: true }).first().click();
  await page.waitForSelector(".profile-lifecycle");
  results.profile = {
    buttons: await page.locator(".profile-lifecycle button").allInnerTexts(),
    record_review_button: await page.getByRole("button", { name: "Record review" }).count(),
    reviewer_text: await page.locator(".profile-reviewer").innerText(),
  };
  await page.locator(".profile-lifecycle").scrollIntoViewIfNeeded();
  await page.screenshot({ path: `${out}/08-profile-approve-one-step-1440.png` });
  await page.getByRole("button", { name: "Approve version" }).click();
  await page.waitForSelector(".active-snapshot");
  results.profile.after_approve_buttons = await page.locator(".profile-lifecycle button").allInnerTexts();
  await page.screenshot({ path: `${out}/08b-profile-approved-1440.png` });
  const readiness = await page.evaluate(async () => {
    const clients = await (await fetch("/api/clients")).json();
    const project = clients.flatMap((c) => c.projects).find((p) => p.name.includes("draft only") && p.framework_version_id.startsWith("hipaa"));
    return (await (await fetch(`/api/projects/${project.id}/profile-readiness`)).json()).state;
  });
  results.profile.readiness_after_approve = readiness;
  await page.close();
}

// 4. The draft CSV: the first line says so.
{
  const page = await browser.newPage({ viewport: { width: 900, height: 360 } });
  const csv = readFileSync(`${csvDir}/DRAFT_Evidence_Index.csv`, "utf8");
  const poam = readFileSync(`${csvDir}/DRAFT_CMMC_POAM_History.csv`, "utf8");
  const esc = (t) => t.replace(/&/g, "&amp;").replace(/</g, "&lt;");
  await page.setContent(`<body style="font:14px ui-monospace,monospace;padding:20px">
    <h3 style="font-family:sans-serif;margin:0 0 6px">DRAFT_Evidence_Index.csv</h3><pre style="background:#f6f8fa;padding:10px;border:1px solid #d0d7de">${esc(csv)}</pre>
    <h3 style="font-family:sans-serif;margin:14px 0 6px">DRAFT_CMMC_POAM_History.csv</h3><pre style="background:#f6f8fa;padding:10px;border:1px solid #d0d7de">${esc(poam)}</pre></body>`);
  await page.screenshot({ path: `${out}/09-draft-csv-first-line.png` });
  results.csv_first_lines = [csv.split("\n")[0], poam.split("\n")[0]];
  await page.close();
}

// 5. A failed backup: the message, nothing issued, the dialog stays open.
{
  const page = await openReady(process.env.FAILING);
  await reports(page);
  await page.getByRole("button", { name: "Review and issue…" }).click();
  await page.waitForSelector(".review-issue-dialog .issue-worth-checking");
  await page.getByLabel(/Note/).fill("October report for the clinic.");
  await page.getByRole("button", { name: "Issue", exact: true }).click();
  await page.waitForSelector(".review-issue-dialog [role=alert]");
  results.backup_failure = {
    message: (await page.locator(".review-issue-dialog [role=alert]").innerText()).replace(/\s+/g, " "),
    dialog_still_open: await page.locator(".review-issue-dialog").count(),
    issued_versions_after: await page.evaluate(async () => {
      const clients = await (await fetch("/api/clients")).json();
      const project = clients.flatMap((c) => c.projects).find((p) => p.name.includes("ready"));
      const packages = await (await fetch(`/api/projects/${project.id}/packages`)).json();
      return packages.map((p) => p.lifecycle);
    }),
  };
  await page.screenshot({ path: `${out}/10-backup-failure-nothing-issued-1440.png` });
  await page.close();
}

// 6. One act, start to finish.
{
  const page = await openReady(process.env.READY);
  await reports(page);
  await page.getByRole("button", { name: "Review and issue…" }).click();
  await page.waitForSelector(".review-issue-dialog .issue-worth-checking");
  await page.getByLabel(/Note/).fill("October report for the clinic.");
  await page.getByRole("button", { name: "Issue", exact: true }).click();
  await page.waitForSelector(".readiness-ok");
  await page.waitForSelector(".issued-versions .generated-package");
  results.issued = {
    banner: (await page.locator(".readiness-ok").innerText()).replace(/\s+/g, " "),
    versions: await page.locator(".issued-versions .generated-package > div:first-child").allInnerTexts(),
  };
  await page.screenshot({ path: `${out}/11-issued-in-one-act-1440.png` });
  await page.close();
}

console.log(JSON.stringify(results, null, 2));
await browser.close();
