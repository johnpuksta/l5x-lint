#!/usr/bin/env node
"use strict";

const { execFileSync } = require("child_process");
const { existsSync } = require("fs");
const { join } = require("path");

const ext = process.platform === "win32" ? ".exe" : "";
const bin = join(__dirname, `l5x-lint${ext}`);

if (!existsSync(bin)) {
  console.error(
    "l5x-lint binary not found. Run 'npm run postinstall' or reinstall."
  );
  process.exit(1);
}

try {
  execFileSync(bin, process.argv.slice(2), { stdio: "inherit" });
} catch (e) {
  process.exitCode = e.status || 1;
}
