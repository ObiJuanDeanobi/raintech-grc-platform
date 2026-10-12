// Render a draft CSV as a picture of its first rows (the file as it opens in a spreadsheet).
// Usage: node docs/evidence/issue-146/render_csv.mjs <csv> <png> [rows]
import { readFileSync } from "node:fs";
import { chromium } from "/opt/node22/lib/node_modules/playwright/index.mjs";

const [csv, png, rows = "16"] = process.argv.slice(2);
const lines = readFileSync(csv, "utf8").split("\n").filter((line, index) => index < Number(rows));

function cells(line) {
  const out = [];
  let current = "";
  let quoted = false;
  for (const ch of line) {
    if (ch === '"') quoted = !quoted;
    else if (ch === "," && !quoted) { out.push(current); current = ""; }
    else current += ch;
  }
  out.push(current);
  return out;
}
const escape = (text) => text.replace(/&/g, "&amp;").replace(/</g, "&lt;");
const body = lines.map((line, i) => `<tr class="${i === 0 ? "banner" : ""}">${cells(line).map((c) => `<td>${escape(c)}</td>`).join("")}</tr>`).join("");
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 400 } });
await page.setContent(`<style>body{font:12px Inter,Arial,sans-serif;margin:12px}table{border-collapse:collapse}td{border:1px solid #cfd8dc;padding:3px 8px;max-width:360px;vertical-align:top}.banner td{background:#fde8e8;color:#c00000;font-weight:700;font-size:14px}</style><table>${body}</table>`);
await page.screenshot({ path: png, fullPage: true });
await browser.close();
