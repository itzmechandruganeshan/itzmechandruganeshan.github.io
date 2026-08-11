/**
 * Visual capture script for debugging UI issues.
 *
 * What it does: opens the given local dev URL in a real headless browser
 * and saves screenshots at three standard viewport widths (mobile, tablet,
 * desktop), plus grabs any console errors that fired while the page loaded.
 *
 * Why: reasoning about layout/CSS bugs directly from source code is
 * unreliable — the agent should look at actual rendered pixels before
 * deciding what's wrong, the same way a human developer opens devtools.
 *
 * Requires: `npx playwright install chromium` once, and the Next.js dev
 * server already running (npm run dev) on the target URL.
 *
 * Usage:
 *   node scripts/capture.mjs http://localhost:3000 ./screenshots
 *   node scripts/capture.mjs http://localhost:3000/projects ./screenshots
 */

import { chromium } from "playwright";
import path from "node:path";
import fs from "node:fs";

const url = process.argv[2] || "http://localhost:3000";
const outDir = process.argv[3] || "./screenshots";

const viewports = [
  { name: "mobile", width: 375, height: 812 },
  { name: "tablet", width: 768, height: 1024 },
  { name: "desktop", width: 1440, height: 900 },
];

fs.mkdirSync(outDir, { recursive: true });

const browser = await chromium.launch();

for (const vp of viewports) {
  const context = await browser.newContext({
    viewport: { width: vp.width, height: vp.height },
  });
  const page = await context.newPage();

  const consoleErrors = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text());
  });
  page.on("pageerror", (err) => consoleErrors.push(String(err)));

  await page.goto(url, { waitUntil: "networkidle" });
  // Let scroll-triggered animations (whileInView, etc.) settle.
  await page.waitForTimeout(800);

  const filePath = path.join(outDir, `${vp.name}-full.png`);
  await page.screenshot({ path: filePath, fullPage: true });

  console.log(`[${vp.name}] saved -> ${filePath}`);
  if (consoleErrors.length) {
    console.log(`[${vp.name}] console errors:`);
    consoleErrors.forEach((e) => console.log("  -", e));
  } else {
    console.log(`[${vp.name}] no console errors`);
  }

  await context.close();
}

await browser.close();
