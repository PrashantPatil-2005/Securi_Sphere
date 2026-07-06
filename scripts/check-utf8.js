#!/usr/bin/env node
/**
 * Reject UTF-16 encoded .tsx/.ts files (common Windows corruption).
 * Usage: node scripts/check-utf8.js
 */
const fs = require("fs");
const path = require("path");

const ROOT = path.join(__dirname, "..", "frontend");
const EXT = new Set([".ts", ".tsx", ".js", ".jsx"]);
const bad = [];

function walk(dir) {
  for (const name of fs.readdirSync(dir)) {
    if (name === "node_modules" || name === ".next") continue;
    const full = path.join(dir, name);
    const st = fs.statSync(full);
    if (st.isDirectory()) walk(full);
    else if (EXT.has(path.extname(name))) {
      const buf = fs.readFileSync(full);
      if (buf.length >= 2 && buf[0] === 0xff && buf[1] === 0xfe) {
        bad.push(path.relative(ROOT, full));
      }
    }
  }
}

walk(ROOT);

if (bad.length) {
  console.error("UTF-16 encoded source files detected (convert to UTF-8):");
  bad.forEach((f) => console.error("  " + f));
  process.exit(1);
}
console.log("UTF-8 check passed.");
