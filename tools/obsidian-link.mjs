#!/usr/bin/env node

import { execFileSync } from "node:child_process";
import path from "node:path";

function usage() {
  console.log(`Usage:
  node tools/obsidian-link.mjs <markdown-file>
  node tools/obsidian-link.mjs --open <markdown-file>

Examples:
  node tools/obsidian-link.mjs 30-projects/经营分析AI知识库数据处理与知识建模调研.md
  node tools/obsidian-link.mjs --open 30-projects/经营分析AI知识库数据处理与知识建模调研.md`);
}

const args = process.argv.slice(2);
const shouldOpen = args[0] === "--open";
const fileArg = shouldOpen ? args[1] : args[0];

if (!fileArg || args.includes("-h") || args.includes("--help")) {
  usage();
  process.exit(fileArg ? 0 : 1);
}

const absolutePath = path.resolve(process.cwd(), fileArg);
const uri = `obsidian://open?path=${encodeURIComponent(absolutePath)}&paneType=tab`;
const label = path.basename(absolutePath).replace(/\.md$/i, "");

if (shouldOpen) {
  execFileSync("open", [uri], { stdio: "ignore" });
}

console.log(`[${label}](${uri})`);
console.log(uri);
