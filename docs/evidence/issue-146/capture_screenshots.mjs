// Capture #146 evidence against a running app seeded with seed_half_done.py (synthetic data only).
// Usage: PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers APP=http://127.0.0.1:18482/ MODE=half|decided \
//   FILES=<dir> node docs/evidence/issue-146/capture_screenshots.mjs <out-dir>
// MODE=half (seed MODE=half): finalize is blocked by undecided objectives; the draft still downloads.
// MODE=decided (seed MODE=decided): the gap assessment finalizes with Not Met work.
// FILES receives the downloaded drafts and issued files (not committed); it prints what it measured.
import { mkdirSync, writeFileSync } from "node:fs";
import { chromium } from "/opt/node22/lib/node_modules/playwright/index.mjs";

const out = process.argv[2];
const base = process.env.APP;
const mode = process.env.MODE ?? "decided";
mkdirSync(process.env.FILES, { recursive: true });
const browser = await chromium.launch();
const results = { mode };
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

await page.goto(base);
await page.waitForSelector(".topbar nav");
await page.getByRole("button", { name: "Reports", exact: true }).first().click();
await page.getByRole("button", { name: "Download draft" }).waitFor();
await page.waitForTimeout(500);
if (mode === "decided") await page.screenshot({ path: `${out}/01-reports-tab-with-package-choice-1440.png` });
results.reports_choice = await page.locator(".reports-actions .package-choice label").allInnerTexts();

const project = (await (await fetch(`${base}api/clients`)).json())[0].projects[0].id;
const assessment = (await (await fetch(`${base}api/projects/${project}/assessment`)).json()).id;
async function save(url, name) {
  const response = await fetch(url);
  results[name] = { status: response.status, disposition: response.headers.get("content-disposition") };
  writeFileSync(`${process.env.FILES}/${name}`, Buffer.from(await response.arrayBuffer()));
}
const draft = `${base}api/projects/${project}/assessments/${assessment}/draft`;
await save(draft, `${mode}-draft-default.zip`);
await save(`${draft}?package=readiness_close`, `${mode}-draft-close.zip`);

await page.getByRole("button", { name: "Review and issue…" }).click();
const dialog = page.getByRole("dialog");
await dialog.locator("input[type=radio]:checked").waitFor();
await dialog.getByRole("button", { name: "Issue", exact: true }).waitFor();
await page.waitForTimeout(600);
results.dialog_default_checked = await dialog.locator("input[type=radio]:checked").evaluate((el) => el.value);
results.gap_must_fix = (await dialog.locator(".issue-must-fix li").allInnerTexts()).map((t) => t.replace(/\s+/g, " "));
results.gap_warnings = (await dialog.locator(".issue-worth-checking li").allInnerTexts()).map((t) => t.replace(/\s+/g, " "));
results.gap_issue_enabled = await dialog.getByRole("button", { name: "Issue", exact: true }).isEnabled();

if (mode === "half") {
  await dialog.screenshot({ path: `${out}/09-half-done-finalize-blocked-undecided.png` });
  console.log(JSON.stringify(results, null, 2));
  await browser.close();
  process.exit(0);
}

await dialog.screenshot({ path: `${out}/02-finalize-dialog-gap-assessment-default.png` });

// The other option keeps its own gates.
await dialog.getByRole("radio", { name: /Final self-assessment/ }).check();
await dialog.locator(".issue-must-fix").waitFor();
await page.waitForTimeout(300);
results.close_must_fix = (await dialog.locator(".issue-must-fix li").allInnerTexts()).map((t) => t.replace(/\s+/g, " "));
results.close_issue_enabled = await dialog.getByRole("button", { name: "Issue", exact: true }).isEnabled();
await dialog.screenshot({ path: `${out}/03-finalize-dialog-final-self-assessment-blocked.png` });
await dialog.getByRole("radio", { name: /^Gap assessment/ }).check();
await dialog.locator(".issue-must-fix").waitFor({ state: "detached" });

// One finalize on a project where every objective is decided, with Not Met work.
await dialog.getByLabel(/Note/).fill("Gap assessment for the kickoff meeting.");
await dialog.getByRole("button", { name: "Issue", exact: true }).click();
await page.getByText(/Issued\. Reviewed by/).waitFor();
await page.waitForTimeout(600);
results.issued_banner = await page.locator(".readiness-ok").innerText();
results.issued_files = await page.locator(".issued-versions .generated-components a").allInnerTexts();
await page.screenshot({ path: `${out}/10-finalized-gap-assessment-1440.png` });

const packages = await (await fetch(`${base}api/projects/${project}/packages`)).json();
const issued = packages.find((p) => p.lifecycle === "Issued");
results.issued_lifecycle = issued.lifecycle;
for (const component of issued.components) {
  const response = await fetch(`${base}api/projects/${project}/packages/${issued.id}/components/${component.id}`);
  writeFileSync(`${process.env.FILES}/issued-${component.filename}`, Buffer.from(await response.arrayBuffer()));
}
console.log(JSON.stringify(results, null, 2));
await browser.close();
