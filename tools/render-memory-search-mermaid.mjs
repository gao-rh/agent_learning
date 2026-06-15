import fs from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { chromium } = require("/Users/gaoronghui/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright");

const root = process.cwd();
const input = path.join(root, "assets/concepts/memory-search-overview.mmd");
const output = path.join(root, "assets/concepts/memory-search-overview.png");
const source = await fs.readFile(input, "utf8");

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({
  viewport: { width: 2400, height: 1800 },
  deviceScaleFactor: 2,
});

await page.setContent(`<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <style>
      html, body {
        margin: 0;
        padding: 0;
        background: #ffffff;
        font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Noto Sans CJK SC", "Microsoft YaHei", Arial, sans-serif;
      }
      #wrap {
        display: inline-block;
        padding: 32px;
        background: #ffffff;
      }
      #diagram > svg {
        width: 1600px !important;
        height: auto !important;
      }
      svg {
        max-width: none;
      }
    </style>
  </head>
  <body>
    <div id="wrap">
      <div id="diagram"></div>
    </div>
    <script type="module">
      import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";
      mermaid.initialize({
        startOnLoad: false,
        securityLevel: "loose",
        theme: "base",
        themeVariables: {
          fontFamily: '-apple-system, BlinkMacSystemFont, "PingFang SC", "Noto Sans CJK SC", "Microsoft YaHei", Arial, sans-serif',
          primaryColor: "#eef6ff",
          primaryBorderColor: "#3b82f6",
          primaryTextColor: "#172033",
          lineColor: "#64748b",
          secondaryColor: "#f7f3ff",
          tertiaryColor: "#f2fbf6",
          clusterBkg: "#ffffff",
          clusterBorder: "#cbd5e1"
        },
        flowchart: {
          curve: "basis",
          nodeSpacing: 42,
          rankSpacing: 58,
          htmlLabels: true
        }
      });
      const source = ${JSON.stringify(source)};
      const { svg } = await mermaid.render("memorySearchOverview", source);
      document.querySelector("#diagram").innerHTML = svg;
      window.__renderDone = true;
    </script>
  </body>
</html>`, { waitUntil: "domcontentloaded" });

await page.waitForFunction(() => window.__renderDone === true, null, { timeout: 30000 });
const box = await page.locator("#wrap").boundingBox();
if (!box) throw new Error("Diagram wrapper was not rendered");
await page.screenshot({
  path: output,
  clip: {
    x: Math.max(0, box.x),
    y: Math.max(0, box.y),
    width: Math.ceil(box.width),
    height: Math.ceil(box.height),
  },
});
await browser.close();
console.log(output);
