// Copies the numbering engine from the Obsidian plugin repo, so Notepad++ runs
// the same tested core. Run after every plugin release:  npm run sync-core
"use strict";
const fs = require("fs");
const path = require("path");
const src = process.argv[2] || path.join(__dirname, "..", "..", "obsidian-nested-outline", "main.js");
const dst = path.join(__dirname, "..", "server", "mni-core.js");
const manifest = JSON.parse(fs.readFileSync(path.join(path.dirname(src), "manifest.json"), "utf8"));
fs.copyFileSync(src, dst);
fs.writeFileSync(path.join(__dirname, "..", "server", "CORE_VERSION"), manifest.version + "\n");
console.log("core " + manifest.version + " -> " + dst);
