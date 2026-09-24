#!/usr/bin/env node

import { spawnSync } from "node:child_process";

const result = spawnSync("pyffmpegcore", process.argv.slice(2), { stdio: "inherit" });

if (result.error) {
  if (result.error.code === "ENOENT") {
    console.error("PyFFmpegCore is not installed. Run: python -m pip install pyffmpegcore");
  } else {
    console.error(`Could not start PyFFmpegCore: ${result.error.message}`);
  }
  process.exit(127);
}

process.exit(result.status ?? 1);
