// Capture #140 evidence screenshots and measurements against the running app.
import { chromium } from "/opt/node22/lib/node_modules/playwright/index.mjs";

const out = process.argv[2];
const base = "http://127.0.0.1:5173/";
const results = {};

const browser = await chromium.launch();

async function open(width, height) {
  const page = await browser.newPage({ viewport: { width, height } });
  page.on("dialog", (dialog) => dialog.accept());
  await page.goto(base);
  await settled(page);
  return page;
}

async function settled(page) {
  await page.waitForSelector(".requirement-workspace h1");
  await page.waitForSelector(".cmmc-score-line");
  await page.waitForSelector(".implementation-statement textarea");
  await page.waitForSelector(".linked-evidence .evidence-list");
  await page.waitForTimeout(150);
}

async function row(page, letter, requirement) {
  return page.locator(`li[aria-label$="${requirement}[${letter}]"]`);
}

// ---------- 1440 x 900 ----------
{
  const page = await open(1440, 900);
  results.landing_requirement_1440 = await page.locator(".requirement-workspace h1").innerText();
  const first = await page.locator(".objective-item").first().boundingBox();
  results.first_objective_row_y_1440 = Math.round(first.y);
  await page.screenshot({ path: `${out}/01-requirement-view-1440.png` });

  // Decide AC.L2-3.1.2 entirely from this view and count record transitions.
  const titles = [];
  const observeTitle = async () => titles.push(await page.locator(".requirement-workspace h1").innerText());
  await observeTitle();
  const objectiveB = page.locator(".objective-item").nth(1);
  await objectiveB.getByRole("button", { name: "Met", exact: true }).click();
  await objectiveB.locator(".routine-save-reason").waitFor();
  results.failed_save_reason = await objectiveB.locator(".routine-save-state").innerText();
  results.failed_save_pressed = await objectiveB.locator('button[aria-pressed="true"]').allInnerTexts();
  await page.screenshot({ path: `${out}/02-failed-save-1440.png` });
  await observeTitle();
  await objectiveB.getByRole("button", { name: /^Notes for/ }).click();
  await objectiveB.getByRole("textbox", { name: /^Interview or observation record/ }).fill("Synthetic: observed role-based menus with the IT lead.");
  // Leaving the field re-sends the pending Met with the observation; the API now accepts it.
  await page.locator(".requirement-head h1").click();
  await page.waitForFunction(() => {
    const items = document.querySelectorAll(".objective-item");
    return items[1]?.querySelector('button[aria-pressed="true"]')?.textContent === "Met";
  });
  await observeTitle();
  results.titles_while_deciding = titles;
  results.page_transitions_to_decide_requirement = new Set(titles).size - 1;
  await page.waitForFunction(() => document.querySelector(".requirement-head .status-pill")?.textContent?.includes("Not Met"));
  results.score_line_after = await page.locator(".cmmc-score-line").innerText();

  // Requirement with six objectives: are they all on screen at 1440x900?
  await page.locator(".requirement-row", { hasText: "AC.L2-3.1.1" }).first().click();
  await page.waitForFunction(() => document.querySelector(".requirement-workspace h1")?.textContent?.startsWith("Authorized Access Control"));
  await settled(page);
  const items = page.locator(".objective-item");
  results.objectives_on_ac_3_1_1 = await items.count();
  const last = await items.last().boundingBox();
  results.last_objective_row_bottom_1440 = Math.round(last.y + last.height);
  results.first_objective_row_y_ac_3_1_1_1440 = Math.round((await items.first().boundingBox()).y);
  await page.screenshot({ path: `${out}/03-requirement-view-six-objectives-1440.png` });

  // Interview view.
  await page.getByRole("button", { name: "Interview view" }).click();
  await page.getByRole("button", { name: /Next objective/ }).click();
  await page.screenshot({ path: `${out}/04-interview-view-1440.png` });
  await page.getByRole("button", { name: "Requirement view" }).click();

  // Left list with family counts: open a second family too.
  await page.locator(".family-header", { hasText: /^AC/ }).click();
  await page.locator(".family-header", { hasText: /^AU/ }).click();
  await page.locator(".rail").screenshot({ path: `${out}/05-family-list-1440.png` });
  results.family_counts = await page.locator(".family-header").evaluateAll((nodes) =>
    nodes.map((node) => node.textContent));
  await page.close();
}

// ---------- ~800 wide ----------
{
  const page = await open(800, 900);
  results.landing_requirement_800 = await page.locator(".requirement-workspace h1").innerText();
  results.first_objective_row_y_800 = Math.round((await page.locator(".objective-item").first().boundingBox()).y);
  results.horizontal_overflow_800 = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  await page.screenshot({ path: `${out}/06-requirement-view-800.png` });
  // Keyboard: Pending is saved; Met without evidence is refused with its reason.
  await page.keyboard.press("m");
  await page.locator(".objective-item.focused .routine-save-reason").waitFor();
  await page.screenshot({ path: `${out}/07-failed-save-800.png` });
  await page.locator(".objective-item.focused").getByRole("button", { name: "Pending", exact: true }).click();
  await page.getByRole("button", { name: "Interview view" }).click();
  await page.screenshot({ path: `${out}/08-interview-view-800.png` });
  await page.locator(".family-header", { hasText: /^AC/ }).click();
  await page.locator(".rail").screenshot({ path: `${out}/09-family-list-800.png` });
  await page.close();
}

await browser.close();
console.log(JSON.stringify(results, null, 2));
