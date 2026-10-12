// Capture #144 evidence screenshots and page heights against running apps (synthetic data only).
// Usage: PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers NEW=http://127.0.0.1:18443/ HALF=http://127.0.0.1:18444/ \
//   HIPAA=http://127.0.0.1:18455/ node docs/evidence/issue-144/capture_screenshots.mjs <out-dir>
// Seed each app first with docs/evidence/issue-144/seed_synthetic_projects.py (MODE=new|half|hipaa).
import { chromium } from "/opt/node22/lib/node_modules/playwright/index.mjs";

const out = process.argv[2];
const browser = await chromium.launch();
const results = {};

async function overview(base) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await page.goto(base);
  await page.waitForSelector(".topbar nav");
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

// New CMMC project.
{
  const page = await overview(process.env.NEW);
  results.new_cmmc = await heights(page);
  await page.screenshot({ path: `${out}/01-new-cmmc-overview-1440.png` });
  await page.close();
}

// Half-done CMMC project with NOT MET items, then one grouped count opened.
{
  const page = await overview(process.env.HALF);
  results.half_cmmc = await heights(page);
  await page.screenshot({ path: `${out}/02-half-done-cmmc-overview-1440.png` });
  await page.locator(".overview-dashboard").evaluate((el) => el.scrollTo(0, el.scrollHeight));
  await page.waitForTimeout(300);
  await page.screenshot({ path: `${out}/02b-half-done-cmmc-overview-lower-1440.png` });
  const group = page.locator(".group-counts button", { hasText: "Objectives not decided" });
  results.grouped_count_clicked = (await group.innerText()).replace(/\s+/g, " ");
  await group.click();
  await page.waitForSelector(".list-filter-chip");
  await page.waitForTimeout(600);
  results.chip = (await page.locator(".list-filter-chip").innerText()).replace(/\s+/g, " ");
  results.filtered_requirement_rows = await page.locator(".requirement-row").count();
  await page.screenshot({ path: `${out}/04-grouped-count-opens-filtered-list-1440.png` });
  await page.close();
}

// HIPAA.
{
  const page = await overview(process.env.HIPAA);
  results.hipaa = await heights(page);
  await page.screenshot({ path: `${out}/03-hipaa-overview-1440.png` });
  await page.close();
}

console.log(JSON.stringify(results, null, 2));
await browser.close();
