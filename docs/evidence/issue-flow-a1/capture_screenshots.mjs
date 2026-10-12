// Capture flow-alignment (ADR 0022) evidence screenshots and page heights against running apps
// (synthetic data only).
// Usage: PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers NEW=http://127.0.0.1:18461/ HALF=http://127.0.0.1:18462/ \
//   HIPAA=http://127.0.0.1:18463/ node docs/evidence/issue-flow-a1/capture_screenshots.mjs <out-dir>
// Seed each app first with docs/evidence/issue-flow-a1/seed_synthetic_projects.py (MODE=new|half|hipaa).
import { chromium } from "/opt/node22/lib/node_modules/playwright/index.mjs";

const out = process.argv[2];
const browser = await chromium.launch();
const results = {};
const BANNED = ["left before issue", "not approved", "FAIL", "Final determination required", "Show every item"];

async function open(base) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await page.goto(base);
  await page.waitForSelector(".topbar nav");
  return page;
}

async function overview(base) {
  const page = await open(base);
  await page.getByRole("button", { name: "Overview", exact: true }).first().click();
  await page.waitForSelector(".overview-dashboard .step-rail");
  await page.waitForTimeout(800);
  return page;
}

const heights = (page) =>
  page.evaluate(() => ({
    document: document.documentElement.scrollHeight,
    overviewPanel: document.querySelector(".overview-dashboard").scrollHeight,
    viewport: window.innerHeight,
  }));

const text = async (page) => (await page.locator(".overview-dashboard").innerText()).replace(/\s+/g, " ");
const flat = async (locator) => (await locator.innerText()).replace(/\s+/g, " ");

// New CMMC project: Not started, checks grey, nothing red, no blocker words.
{
  const page = await overview(process.env.NEW);
  results.new_cmmc = await heights(page);
  const body = await text(page);
  results.new_cmmc_banned_words = BANNED.filter((word) => body.includes(word));
  results.new_cmmc_step_rail = await flat(page.locator(".step-rail"));
  results.new_cmmc_score_panel = (await flat(page.locator(".cmmc-score"))).slice(0, 400);
  results.new_cmmc_red_elements = await page.locator(".overview-dashboard .fail").count();
  await page.screenshot({ path: `${out}/01-new-cmmc-overview-1440.png` });
  // The only place blockers appear: the finalize dialog.
  await page.getByRole("button", { name: "Deliverables", exact: true }).click();
  await page.waitForSelector("text=Final versions");
  await page.screenshot({ path: `${out}/05-deliverables-tab-1440.png` });
  await page.getByRole("button", { name: "Finalize…" }).click();
  await page.waitForSelector("text=Fix before finalizing");
  await page.waitForTimeout(400);
  results.finalize_dialog = (await flat(page.locator(".review-issue-dialog"))).slice(0, 700);
  await page.screenshot({ path: `${out}/06-finalize-dialog-blockers-1440.png` });
  await page.close();
}

// Half-done CMMC project: progress figures, then one figure opened as a filtered list.
{
  const page = await overview(process.env.HALF);
  results.half_cmmc = await heights(page);
  const body = await text(page);
  results.half_cmmc_banned_words = BANNED.filter((word) => body.includes(word));
  results.half_cmmc_step_rail = await flat(page.locator(".step-rail"));
  results.half_cmmc_score_panel = (await flat(page.locator(".cmmc-score"))).slice(0, 400);
  await page.screenshot({ path: `${out}/02-half-done-cmmc-overview-1440.png` });
  await page.locator(".overview-dashboard").evaluate((el) => el.scrollTo(0, el.scrollHeight));
  await page.waitForTimeout(300);
  await page.screenshot({ path: `${out}/02b-half-done-cmmc-overview-lower-1440.png` });
  await page.locator(".overview-dashboard").evaluate((el) => el.scrollTo(0, 0));
  const figure = page.locator(".step-rail .step-figures button", { hasText: "decided" });
  results.figure_clicked = await flat(figure);
  await figure.click();
  await page.waitForSelector(".list-filter-chip");
  await page.waitForTimeout(600);
  results.chip = await flat(page.locator(".list-filter-chip"));
  results.filtered_requirement_rows = await page.locator(".requirement-row").count();
  await page.screenshot({ path: `${out}/04-progress-figure-opens-filtered-list-1440.png` });
  await page.getByRole("button", { name: "Evidence", exact: true }).first().click();
  await page.waitForSelector(".evidence-filters");
  await page.getByRole("button", { name: /Requirements with no evidence/ }).click();
  await page.waitForSelector(".evidence-coverage");
  results.evidence_filters = await flat(page.locator(".evidence-filters"));
  await page.screenshot({ path: `${out}/07-evidence-coverage-1440.png` });
  await page.close();
}

// HIPAA.
{
  const page = await overview(process.env.HIPAA);
  results.hipaa = await heights(page);
  const body = await text(page);
  results.hipaa_banned_words = [...BANNED, "Objectives"].filter((word) => body.includes(word));
  results.hipaa_step_rail = await flat(page.locator(".step-rail"));
  await page.screenshot({ path: `${out}/03-hipaa-overview-1440.png` });
  await page.getByRole("button", { name: "Deliverables", exact: true }).click();
  await page.getByRole("button", { name: "Finalize…" }).click();
  await page.waitForSelector("text=Fix before finalizing");
  await page.waitForTimeout(400);
  results.hipaa_finalize = (await flat(page.locator(".review-issue-dialog"))).slice(0, 700);
  await page.screenshot({ path: `${out}/08-hipaa-finalize-dialog-1440.png` });
  await page.close();
}

console.log(JSON.stringify(results, null, 2));
await browser.close();
