// Capture Clients home evidence screenshots (synthetic data only).
// Seed one app with docs/evidence/issue-144/seed_synthetic_projects.py, run with MODE=new, half and
// hipaa against the same data dir, then:
//   PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers BASE=http://127.0.0.1:18497/ \
//     node docs/evidence/issue-clients-home/capture_screenshots.mjs <out-dir>
import { chromium } from "/opt/node22/lib/node_modules/playwright/index.mjs";

const out = process.argv[2];
const base = process.env.BASE;
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const measured = {};

// First screen: more than one project opens on the Clients home.
const started = Date.now();
await page.goto(base);
await page.waitForSelector(".home-card");
measured.home_cards_visible_ms = Date.now() - started;
await page.waitForTimeout(300);
await page.screenshot({ path: `${out}/01-clients-home-1440.png` });

// Search narrows the cards.
const search = page.getByRole("searchbox", { name: "Search clients and projects" });
await search.fill("harbor");
await page.waitForTimeout(200);
await page.screenshot({ path: `${out}/02-clients-home-search-1440.png` });
await search.fill("");

// A card opens that project's Overview; the logo returns to the home.
await page.getByRole("button", { name: /^Redwood Aerospace Ltd/ }).click();
await page.waitForSelector(".overview-dashboard .step-rail");
await page.waitForTimeout(500);
await page.screenshot({ path: `${out}/03-card-opens-project-overview-1440.png` });
await page.getByRole("button", { name: /back to all clients/ }).click();
await page.waitForSelector(".home-card");
await page.waitForTimeout(300);
await page.screenshot({ path: `${out}/04-logo-returns-to-home-1440.png` });

console.log(JSON.stringify(measured));
await browser.close();
