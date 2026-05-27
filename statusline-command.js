#!/usr/bin/env node
// Claude Code statusLine. Reads session JSON on stdin, prints a compact line.
// Dependency-free (no jq). Cross-platform: needs only node + git on PATH.

"use strict";

const os = require("os");
const path = require("path");
const { execFileSync } = require("child_process");

const C = {
  reset: "\x1b[0m",
  dim: "\x1b[2m",
  cyan: "\x1b[36m",
  green: "\x1b[32m",
  yellow: "\x1b[33m",
  red: "\x1b[31m",
};

function readStdin() {
  try {
    return require("fs").readFileSync(0, "utf8");
  } catch {
    return "";
  }
}

function shortenHome(dir) {
  if (!dir) return "?";
  const home = os.homedir();
  const n = (p) => p.replace(/\\/g, "/").replace(/\/+$/, "");
  const nd = n(dir);
  const nh = n(home);
  if (nh && (nd === nh || nd.toLowerCase().startsWith(nh.toLowerCase() + "/"))) {
    return "~" + nd.slice(nh.length);
  }
  return nd;
}

function gitSegment(dir) {
  try {
    const branch = execFileSync("git", ["-c", "core.checkStat=minimal", "--no-optional-locks", "branch", "--show-current"], {
      cwd: dir,
      stdio: ["ignore", "pipe", "ignore"],
      encoding: "utf8",
    }).trim();
    if (!branch) return "";
    let dirty = "";
    try {
      const status = execFileSync("git", ["--no-optional-locks", "status", "--porcelain"], {
        cwd: dir,
        stdio: ["ignore", "pipe", "ignore"],
        encoding: "utf8",
      });
      if (status.trim()) dirty = "*";
    } catch {
      /* ignore */
    }
    const color = dirty ? C.yellow : C.green;
    return ` ${C.dim}(${C.reset}${color}${branch}${dirty}${C.reset}${C.dim})${C.reset}`;
  } catch {
    return "";
  }
}

const raw = readStdin().replace(/^﻿/, "");
let data = {};
try {
  data = JSON.parse(raw);
} catch {
  /* leave defaults */
}

const dir =
  (data.workspace && data.workspace.current_dir) || data.cwd || process.cwd();
const model = (data.model && data.model.display_name) || "Claude";
const usedPct =
  data.context_window && data.context_window.used_percentage != null
    ? data.context_window.used_percentage
    : null;

const dirSeg = `${C.cyan}${shortenHome(dir)}${C.reset}`;
const git = gitSegment(dir);
const modelSeg = `${C.dim}${model}${C.reset}`;

let ctxSeg = "";
if (usedPct !== null) {
  const pct = Math.round(usedPct);
  const ctxColor = pct >= 80 ? C.red : pct >= 50 ? C.yellow : C.green;
  ctxSeg = `  ${ctxColor}ctx:${pct}%${C.reset}`;
}

process.stdout.write(`${dirSeg}${git}  ${modelSeg}${ctxSeg}`);
