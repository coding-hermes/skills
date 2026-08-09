#!/usr/bin/env node
// Verify every `<prefix> <cmd>` documented in a markdown file exists in the CLI's --help output.
// Proven: wojons-mythos tick #164 (GAP-001 AC3) — docs/reference/cli-commands.md vs
//   node packages/cli/dist/index.js --help  → PASS (documented == advertised).
// Usage:
//   node check_docs_vs_cli_help.js <doc-path> [help-command] [doc-command-prefix]
//   node check_docs_vs_cli_help.js docs/reference/cli-commands.md "node packages/cli/dist/index.js --help" mythos
// Exit 0 = every documented top-level command exists in --help; exit 1 = drift found.
// The --help parse assumes a "COMMANDS:" section followed by an "OPTIONS:" section with
// two-space-indented command names — adjust the regexes if a CLI's help format differs.

const fs = require("fs");
const { execFileSync } = require("child_process");

const docPath = process.argv[2];
if (!docPath) {
  console.error("usage: node check_docs_vs_cli_help.js <doc-path> [help-command] [doc-command-prefix]");
  process.exit(2);
}
const helpCmd = (process.argv[3] || "node packages/cli/dist/index.js --help").split(/\s+/);
const prefix = process.argv[4] || "mythos";

const doc = fs.readFileSync(docPath, "utf8");
const help = execFileSync(helpCmd[0], helpCmd.slice(1), { encoding: "utf8" });

// Every `<prefix> <top-level-cmd>` token in the doc (deduped, sorted).
const documented = [
  ...new Set(
    [...doc.matchAll(new RegExp(`\\b${prefix}\\s+([a-z][a-z-]*)`, "g"))].map((m) => m[1]),
  ),
].sort();

// Top-level commands advertised by --help (COMMANDS: block, 2-space indent).
const commandBlock = help.split("COMMANDS:\n", 2)[1].split("\n\nOPTIONS:", 2)[0];
const advertised = [
  ...new Set(
    [...commandBlock.matchAll(/^\s{2}([a-z][a-z-]*)\b/gm)].map((m) => m[1]),
  ),
].sort();

const missing = documented.filter((c) => !advertised.includes(c));

console.log(`documented top-level commands: ${documented.join(", ") || "(none)"}`);
console.log(`--help top-level commands:      ${advertised.join(", ") || "(none)"}`);
console.log(`missing from --help:            ${missing.join(", ") || "none"}`);
console.log(`result: ${missing.length === 0 ? "PASS" : "FAIL"}`);
process.exitCode = missing.length === 0 ? 0 : 1;
