// Capture POA&M view screenshots against running apps (synthetic data only).
// Usage: PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers HALF=http://127.0.0.1:18483/ HIPAA=http://127.0.0.1:18484/ \
//   node docs/evidence/issue-poam-view/capture_screenshots.mjs <out-dir>
// Seed each app with docs/evidence/issue-144/seed_synthetic_projects.py (MODE=half|hipaa), then add Ready for
// Validation, Closed, Withdrawn and (HIPAA) In Progress / Waiting items through the public API (seed_extra_states.py).
import { chromium } from "/opt/node22/lib/node_modules/playwright/index.mjs";

const out = process.argv[2];
const browser = await chromium.launch();
const results = {};

async function open(base) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await page.goto(base);
  await page.waitForSelector(".topbar nav");
  await page.getByRole("button", { name: /^(POA&M|Corrective actions)$/ }).click();
  await page.waitForSelector(".poam-table");
  return page;
}

// CMMC: all items, then filtered, then a row opened.
{
  const page = await open(process.env.HALF);
  results.cmmc_nav = await page.locator(".topbar nav button").allInnerTexts();
  results.cmmc_progress = await page.locator(".poam-progress").innerText();
  await page.screenshot({ path: `${out}/01-cmmc-poam-list-1440.png` });
  await page.getByLabel("Filter by eligibility").selectOption("eligible");
  results.cmmc_eligible_rows = await page.locator(".poam-row").count();
  await page.screenshot({ path: `${out}/02-cmmc-poam-filtered-eligible-1440.png` });
  await page.getByLabel("Filter by eligibility").selectOption("all");
  await page.getByRole("button", { name: "Open AC.L2-3.1.7" }).click();
  await page.waitForSelector(".requirement-workspace, .record-brief, .requirement-list");
  await page.waitForTimeout(800);
  results.opened_heading = (await page.locator("h1, h2").allInnerTexts()).slice(0, 4);
  await page.screenshot({ path: `${out}/03-row-opens-requirement-1440.png` });
  await page.close();
}

// HIPAA.
{
  const page = await open(process.env.HIPAA);
  results.hipaa_progress = await page.locator(".poam-progress").innerText();
  results.hipaa_columns = await page.locator(".poam-table th").allInnerTexts();
  results.hipaa_nav = await page.locator(".topbar nav button").allInnerTexts();
  await page.screenshot({ path: `${out}/04-hipaa-corrective-actions-1440.png` });
  await page.locator("button.poam-gap").click();
  await page.waitForSelector(".list-filter-chip");
  await page.waitForTimeout(600);
  results.hipaa_gap_chip = (await page.locator(".list-filter-chip").innerText()).replace(/\s+/g, " ");
  await page.screenshot({ path: `${out}/05-hipaa-gap-pill-opens-filtered-list-1440.png` });
  await page.close();
}

console.log(JSON.stringify(results, null, 2));
await browser.close();
