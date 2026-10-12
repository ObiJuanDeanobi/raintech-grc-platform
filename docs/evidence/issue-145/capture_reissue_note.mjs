// After capture_screenshots.mjs has issued once on READY: the dialog now says that issuing
// again replaces the current issued version. Usage: READY=http://127.0.0.1:18460/ node <this> <out-dir>
import { chromium } from "/opt/node22/lib/node_modules/playwright/index.mjs";

const out = process.argv[2];
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
await page.goto(process.env.READY);
await page.waitForSelector(".topbar nav");
const select = page.locator(".project-switcher select");
const option = select.locator("option", { hasText: "HIPAA 2026 (ready to issue)" });
await select.selectOption(await option.getAttribute("value"));
await page.waitForTimeout(1200);
await page.getByRole("button", { name: "Reports", exact: true }).first().click();
await page.getByRole("button", { name: "Review and issue…" }).click();
await page.waitForSelector(".review-issue-dialog [role=note]");
console.log(await page.locator(".review-issue-dialog [role=note]").innerText());
await page.screenshot({ path: `${out}/13-issuing-again-replaces-current-1440.png` });
await browser.close();
