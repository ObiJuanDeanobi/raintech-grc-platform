// Capture #143 evidence screenshots against the running app (synthetic data only).
// Usage: APP_BASE=http://127.0.0.1:5173/ PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers \
//   node docs/evidence/issue-143/capture_screenshots.mjs <out-dir>
// Seed first with docs/evidence/issue-143/seed_synthetic_cmmc.py.
import { chromium } from "/opt/node22/lib/node_modules/playwright/index.mjs";

const out = process.argv[2];
const base = process.env.APP_BASE ?? "http://127.0.0.1:5173/";
const results = {};
const browser = await chromium.launch();

async function open(width, height) {
  const page = await browser.newPage({ viewport: { width, height } });
  await page.goto(base);
  await page.waitForSelector(".requirement-workspace h1");
  await page.waitForSelector(".cmmc-score-line .score-verified");
  return page;
}

async function openRequirement(page, id, title) {
  await page.locator(".requirement-row", { hasText: id }).first().click();
  await page.waitForFunction((t) => document.querySelector(".requirement-workspace h1")?.textContent?.startsWith(t), title);
  await page.waitForSelector(".requirement-finding .poam-section");
  await page.waitForTimeout(400);
}

const countText = (page) => page.locator(".record-toolbar .unplanned-not-met").innerText();
const poamItems = (page, projectId, assessmentId, requirement) =>
  page.evaluate(
    async ([p, a, r]) => (await (await fetch(`/api/projects/${p}/assessments/${a}/requirements/${r}/finding`)).json()).poam_items,
    [projectId, assessmentId, requirement],
  );

// ---------- 1440 x 900 ----------
{
  const page = await open(1440, 900);
  const workspace = await page.evaluate(async () => {
    const clients = await (await fetch("/api/clients")).json();
    const project = clients[0].projects[0].id;
    const assessment = await (await fetch(`/api/projects/${project}/assessment`)).json();
    return { project, assessment: assessment.id, before: assessment.not_met_without_poam };
  });
  results.api_before = workspace.before;
  results.header_count_before = await countText(page);

  // 01: a 5-point NOT MET requirement with the button and the 32 CFR 170.21 warning.
  await openRequirement(page, "AC.L2-3.1.2", "Transaction & Function Control");
  results.button_before = {
    text: await page.getByRole("button", { name: "Create POA&M draft" }).innerText(),
    enabled: await page.getByRole("button", { name: "Create POA&M draft" }).isEnabled(),
  };
  results.warning = await page.locator(".poam-eligibility-warning").innerText();
  await page.locator(".requirement-finding").scrollIntoViewIfNeeded();
  await page.screenshot({ path: `${out}/01-not-met-requirement-with-button-and-170-21-warning-1440.png` });

  // 02: one click creates the prefilled Draft, opened inline with its title focused.
  await page.getByRole("button", { name: "Create POA&M draft" }).click();
  await page.waitForSelector(".poam-draft");
  await page.waitForTimeout(400);
  results.draft = {
    title: await page.locator(".poam-draft input").inputValue(),
    title_focused: await page.locator(".poam-draft input").evaluate((el) => el === document.activeElement),
    description: await page.locator(".poam-draft textarea").inputValue(),
    status_tag: await page.locator(".poam-draft .poam-status").innerText(),
  };
  results.button_after = {
    enabled: await page.getByRole("button", { name: "Create POA&M draft" }).isEnabled(),
    reason: await page.locator(".poam-create .muted-small").innerText(),
  };
  // A forced second click on the disabled button creates nothing.
  await page.getByRole("button", { name: "Create POA&M draft" }).click({ force: true });
  await page.waitForTimeout(300);
  results.items_after_second_click = (await poamItems(page, workspace.project, workspace.assessment, "AC.L2-3.1.2")).map((i) => `${i.title} · ${i.status}`);
  results.header_count_after = await countText(page);
  await page.locator(".requirement-finding").screenshot({ path: `${out}/02-created-draft-inline-1440.png` });

  // 03: the header count, pressed, filters the requirement list.
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.locator(".record-toolbar .unplanned-not-met").click();
  await page.waitForTimeout(300);
  results.filtered_rows = await page.locator(".requirement-list .requirement-row small").allInnerTexts();
  await page.screenshot({ path: `${out}/03-header-count-and-filtered-list-1440.png` });

  // 04: a 1-point requirement is POA&M-eligible: no warning.
  await openRequirement(page, "AC.L2-3.1.3", "Control CUI Flow");
  results.one_point_warning_count = await page.locator(".poam-eligibility-warning").count();
  await page.locator(".requirement-finding").scrollIntoViewIfNeeded();
  await page.locator(".requirement-finding").screenshot({ path: `${out}/04-eligible-requirement-no-warning-1440.png` });

  results.api_after = await page.evaluate(
    async (p) => (await (await fetch(`/api/projects/${p}/assessment`)).json()).not_met_without_poam,
    workspace.project,
  );
  results.score_after = await page.evaluate(
    async ([p, a]) => (await (await fetch(`/api/projects/${p}/assessments/${a}/cmmc-score`)).json()).not_met_without_poam,
    [workspace.project, workspace.assessment],
  );
  await page.close();
}

// ---------- 800 wide ----------
{
  const page = await open(800, 900);
  await openRequirement(page, "AC.L2-3.1.2", "Transaction & Function Control");
  await page.locator(".requirement-finding").scrollIntoViewIfNeeded();
  results.horizontal_overflow_800 = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  await page.screenshot({ path: `${out}/05-draft-and-warning-800.png` });
  await page.close();
}

await browser.close();
console.log(JSON.stringify(results, null, 2));
