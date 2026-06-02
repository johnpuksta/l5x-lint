#!/usr/bin/env node
"use strict";

const { createWriteStream, chmodSync, existsSync, mkdirSync } = require("fs");
const { get } = require("https");
const { join } = require("path");
const { execFileSync } = require("child_process");
const { pipeline } = require("stream/promises");

const PKG = require("./package.json");
const VERSION = PKG.version;

const PLATFORM_MAP = {
  "linux-x64": "linux-x86_64",
  "darwin-x64": "macos-x86_64",
  "darwin-arm64": "macos-arm64",
  "win32-x64": "windows-x86_64.exe",
};

const platform = `${process.platform}-${process.arch}`;
const assetSuffix = PLATFORM_MAP[platform];

if (!assetSuffix) {
  console.error(
    `Unsupported platform: ${platform}. ` +
      `Supported: ${Object.keys(PLATFORM_MAP).join(", ")}`
  );
  process.exit(1);
}

const REPO = "JohnPrice/l5x-lint";
const ASSET = `l5x-lint-${assetSuffix}`;
const URL = `https://github.com/${REPO}/releases/download/v${VERSION}/${ASSET}`;

const BIN_DIR = join(__dirname);
const BIN_PATH = join(BIN_DIR, `l5x-lint${process.platform === "win32" ? ".exe" : ""}`);

async function download(url, dest) {
  const res = await new Promise((resolve, reject) => {
    get(url, (r) => {
      if (r.statusCode >= 300 && r.statusCode < 400 && r.headers.location) {
        get(r.headers.location, resolve).on("error", reject);
      } else if (r.statusCode !== 200) {
        reject(new Error(`HTTP ${r.statusCode} for ${url}`));
      } else {
        resolve(r);
      }
    }).on("error", reject);
  });

  await pipeline(res, createWriteStream(dest));
}

async function main() {
  console.log(`Downloading l5x-lint v${VERSION} for ${platform}...`);

  if (!existsSync(BIN_DIR)) mkdirSync(BIN_DIR, { recursive: true });

  try {
    await download(URL, BIN_PATH);
    chmodSync(BIN_PATH, 0o755);
    console.log(`Installed ${BIN_PATH}`);

    const ver = execFileSync(BIN_PATH, ["--help"], { encoding: "utf8" });
    console.log(ver);
  } catch (err) {
    console.error(`Installation failed: ${err.message}`);
    console.error(
      `Download from: ${URL}`
    );
    process.exit(1);
  }
}

main();
