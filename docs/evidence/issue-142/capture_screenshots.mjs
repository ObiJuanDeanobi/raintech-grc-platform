// Capture #142 evidence screenshots against the running app (synthetic data only).
// Serve: python docs/evidence/issue-140/serve_synthetic_api.py <empty-dir>; pnpm run dev;
// seed: python docs/evidence/issue-142/seed_synthetic_evidence.py
// Usage: PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers node docs/evidence/issue-142/capture_screenshots.mjs <out-dir>
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

async function evidenceView(page) {
  await page.locator(".topbar nav button", { hasText: "Evidence" }).click();
  await page.waitForSelector(".evidence-table");
  await page.waitForTimeout(200);
}

async function requirement(page, id, title) {
  await page.locator(".requirement-row", { hasText: id }).first().click();
  try {
    await page.waitForFunction((name) => document.querySelector(".requirement-workspace h1")?.textContent?.startsWith(name), title, { timeout: 10000 });
  } catch (error) {
    await page.screenshot({ path: `${out}/debug-failure.png` });
    throw error;
  }
  await page.waitForTimeout(400);
}

const rowText = (page) => page.locator(".evidence-table tbody tr.evidence-row").allInnerTexts();

// ---------- 1440 x 900 ----------
{
  const page = await open(1440, 900);
  results.score_line_stale = await page.locator(".cmmc-score-line").innerText();

  await evidenceView(page);
  results.library_rows = await rowText(page);
  await page.screenshot({ path: `${out}/01-evidence-view-current-due-soon-stale-1440.png` });

  const policyRow = page.locator("tr.evidence-row", { hasText: "synthetic-access-control-policy.pdf" });
  await policyRow.getByRole("button", { name: /Used by 3/ }).click();
  await page.waitForSelector(".used-by-row");
  results.used_by = await page.locator(".used-by-row li").allInnerTexts();
  await page.screenshot({ path: `${out}/02-used-by-expanded-1440.png` });

  // Clicking a use opens that objective in the requirement view.
  await page.locator(".used-by-link", { hasText: "3.1.1[b]" }).click();
  await page.waitForSelector(".requirement-workspace .objective-item.evidence-pending");
  await page.waitForTimeout(400);
  results.opened_requirement = await page.locator(".requirement-workspace h1").innerText();
  results.focused_objective = await page.locator(".objective-item.focused .objective-citation").innerText();
  results.rows_after_stale = await page.locator(".objective-item").evaluateAll((rows) => rows.map((row) => ({
    citation: row.querySelector(".objective-citation")?.textContent,
    met_pressed: row.querySelector('.objective-buttons button[aria-pressed="true"]')?.textContent,
    evidence_pending: row.classList.contains("evidence-pending"),
    tags: [...row.querySelectorAll(".evidence-pending-tag, .evidence-review-tag")].map((tag) => tag.textContent?.trim()),
  })));
  await page.screenshot({ path: `${out}/03-requirement-view-met-returned-to-evidence-pending-1440.png` });

  // Multi-objective link picker.
  await page.getByRole("button", { name: "Link evidence" }).click();
  const picker = page.getByRole("form", { name: "Link evidence to objectives" });
  const option = await picker.locator("select option", { hasText: "synthetic-incident-response-plan.docx" }).getAttribute("value");
  await picker.locator("select").selectOption(option);
  await picker.getByRole("checkbox", { name: /3\.1\.1\[d\]/ }).check();
  await picker.getByRole("checkbox", { name: /3\.1\.1\[e\]/ }).check();
  await picker.getByRole("textbox", { name: "Support rationale" }).fill("Synthetic: plan section 4 covers account lockout and access revocation.");
  await picker.scrollIntoViewIfNeeded();
  results.picker_options = await picker.locator("select option").allInnerTexts();
  results.picker_submit = await picker.getByRole("button", { name: /Link to/ }).innerText();
  await page.screenshot({ path: `${out}/04-multi-objective-link-picker-1440.png` });
  await picker.getByRole("button", { name: /Link to/ }).click();
  await page.waitForTimeout(800);

  // Due soon on an objective row.
  await requirement(page, "AC.L2-3.1.2", "Transaction & Function Control");
  results.due_soon_row = await page.locator(".objective-item", { hasText: "3.1.2[a]" }).innerText();
  await page.screenshot({ path: `${out}/05-objective-evidence-due-soon-1440.png` });

  // Renew the stale policy with a current version.
  await evidenceView(page);
  results.library_after_link = await rowText(page);
  const stale = page.locator("tr.evidence-row", { hasText: "synthetic-access-control-policy.pdf" });
  await stale.getByRole("button", { name: /Renew/ }).click();
  const form = page.getByRole("form", { name: "Replace synthetic-access-control-policy.pdf" });
  await form.getByLabel("New version of synthetic-access-control-policy.pdf").setInputFiles({
    name: "synthetic-access-control-policy.pdf", mimeType: "application/pdf", buffer: Buffer.from("Synthetic access control policy v2026."),
  });
  const next = new Date(Date.now() + 365 * 86400000).toISOString().slice(0, 10);
  await form.getByLabel("Next review date").fill(next);
  await page.screenshot({ path: `${out}/06-renew-stale-artifact-1440.png` });
  await form.getByRole("button", { name: /Upload version 2/ }).click();
  await page.waitForFunction(() => !document.querySelector(".renew-form"));
  await page.waitForTimeout(500);
  results.library_after_renewal = await rowText(page);

  await page.locator(".topbar nav button", { hasText: "Assessments" }).click();
  await requirement(page, "AC.L2-3.1.1", "Authorized Access Control");
  await page.waitForTimeout(600);
  results.score_line_renewed = await page.locator(".cmmc-score-line").innerText();
  results.pending_rows_after_renewal = await page.locator(".objective-item.evidence-pending").count();
  await page.screenshot({ path: `${out}/07-requirement-view-verified-after-renewal-1440.png` });
  await page.close();
}

// ---------- 800 wide ----------
{
  const page = await open(800, 900);
  await evidenceView(page);
  await page.locator("tr.evidence-row", { hasText: "synthetic-network-diagram.png" }).getByRole("button", { name: /Used by/ }).click();
  results.horizontal_overflow_800 = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  await page.screenshot({ path: `${out}/08-evidence-view-800.png`, fullPage: true });
  await page.close();
}

await browser.close();
console.log(JSON.stringify(results, null, 2));
