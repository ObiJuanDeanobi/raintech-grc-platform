// Capture #141 evidence screenshots against the running app (synthetic data only).
// Usage: PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers node docs/evidence/issue-141/capture_screenshots.mjs <out-dir>
import { chromium } from "/opt/node22/lib/node_modules/playwright/index.mjs";

const out = process.argv[2];
const base = "http://127.0.0.1:5173/";
const results = {};
const browser = await chromium.launch();

async function open(width, height) {
  const page = await browser.newPage({ viewport: { width, height } });
  page.on("dialog", (dialog) => dialog.accept());
  await page.goto(base);
  await page.waitForSelector(".requirement-workspace h1");
  await page.waitForSelector(".cmmc-score-line .score-verified");
  return page;
}

async function selectProject(page, name) {
  const select = page.locator(".rail select").first();
  const value = await select.locator("option", { hasText: name }).getAttribute("value");
  await select.selectOption(value);
  await page.waitForFunction((label) => document.body.innerText.includes(label), name);
  await page.waitForSelector(".cmmc-score-line .score-verified");
  await page.waitForTimeout(300);
}

async function overview(page) {
  await page.getByRole("button", { name: "Overview" }).first().click();
  await page.waitForSelector(".overview-panel .cmmc-score");
  await page.waitForTimeout(200);
}

// ---------- 1440 x 900, fieldwork project (fails 170.21(a)(2)(ii)) ----------
{
  const page = await open(1440, 900);
  await selectProject(page, "fieldwork (synthetic)");
  await page.locator(".requirement-row", { hasText: "AC.L2-3.1.1" }).first().click();
  await page.waitForFunction(() => document.querySelector(".requirement-workspace h1")?.textContent?.startsWith("Authorized Access Control"));
  await page.waitForSelector(".objective-item.evidence-pending");
  await page.waitForTimeout(300);
  results.requirement = await page.locator(".requirement-workspace h1").innerText();
  results.evidence_pending_rows = await page.locator(".objective-item.evidence-pending").count();
  results.verified_rows = await page.locator(".objective-item:not(.evidence-pending)").count();
  results.score_line = await page.locator(".cmmc-score-line").innerText();
  await page.screenshot({ path: `${out}/01-requirement-view-evidence-pending-1440.png` });

  await page.getByRole("button", { name: /Arithmetic and 170.21 checks/ }).click();
  await page.waitForSelector(".cmmc-score-popover");
  results.popover_arithmetic = await page.locator(".cmmc-score-popover code").allInnerTexts();
  results.popover_checks = await page.locator(".cmmc-score-popover .conditional-checks > ul > li .check-line").allInnerTexts();
  await page.screenshot({ path: `${out}/02-score-arithmetic-and-170-21-failing-1440.png` });
  await page.getByRole("button", { name: /Arithmetic and 170.21 checks/ }).click();

  await page.locator(".family-header", { hasText: /^IA/ }).click();
  await page.locator(".rail").screenshot({ path: `${out}/03-requirement-list-evidence-pending-1440.png` });
  results.list_evidence_pending = await page.locator(".requirement-row", { has: page.locator(".marker.evidence-pending") }).allInnerTexts();

  await overview(page);
  await page.locator(".overview-panel .cmmc-score details summary").click();
  results.overview_fieldwork = await page.locator(".overview-panel .cmmc-score .cmmc-score-head").innerText();
  await page.locator(".overview-panel .cmmc-score").screenshot({ path: `${out}/04-overview-score-170-21-failing-1440.png` });
  await page.close();
}

// ---------- 1440 x 900, conditional project (passes every check) ----------
{
  const page = await open(1440, 900);
  await selectProject(page, "conditional (synthetic)");
  await overview(page);
  await page.locator(".overview-panel .cmmc-score details summary").click();
  results.overview_conditional = await page.locator(".overview-panel .cmmc-score .cmmc-score-head").innerText();
  results.conditional_verdict = await page.locator(".overview-panel .conditional-verdict").innerText();
  await page.locator(".overview-panel .cmmc-score").screenshot({ path: `${out}/05-overview-score-170-21-passing-1440.png` });
  await page.close();
}

// ---------- 800 wide ----------
{
  const page = await open(800, 900);
  await selectProject(page, "fieldwork (synthetic)");
  await page.locator(".requirement-row", { hasText: "AC.L2-3.1.1" }).first().click();
  await page.waitForSelector(".objective-item.evidence-pending");
  await page.getByRole("button", { name: /Arithmetic and 170.21 checks/ }).click();
  await page.waitForSelector(".cmmc-score-popover");
  results.horizontal_overflow_800 = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  await page.screenshot({ path: `${out}/06-requirement-view-score-800.png` });
  await page.close();
}

await browser.close();
console.log(JSON.stringify(results, null, 2));
