#!/usr/bin/env node
// Claude Code status line — futuristic HUD with emoji accents. Reads session JSON on stdin.
//   Line 1:  🤖 MODEL  │  ⚡ EFFORT XHIGH  │  ⏱ UPTIME 6m 12s
//   Line 2:  🧠 CONTEXT ▰▰▱▱… NN% [🔥] [⚠ OVER 200K]

const c = (code, s) => `\x1b[${code}m${s}\x1b[0m`;
const fg = (n, s) => c(`38;5;${n}`, s);
const bold = (s) => c("1", s);

// Palette
const neon = (s) => fg(51, s); // accent cyan
const steel = (s) => fg(66, s); // chrome: labels, separators
const track = (s) => fg(238, s); // unfilled gauge / faint
const SAFE = 48; // neon green
const WARN = 214; // amber
const CRIT = 198; // hot magenta

// Effort tint scales with intensity: low chrome -> hot magenta at max
const EFFORT_COLOR = { low: 66, medium: 80, high: 214, xhigh: 198, max: 198 };

// Ceiling is 30%: safe < 15, warn 15-29, critical 30+
const band = (pct) => (pct >= 30 ? CRIT : pct >= 15 ? WARN : SAFE);

const SEP = steel("  │  ");

function readStdin() {
  return new Promise((resolve) => {
    let data = "";
    process.stdin.setEncoding("utf8");
    process.stdin.on("data", (chunk) => (data += chunk));
    process.stdin.on("end", () => resolve(data));
    setTimeout(() => resolve(data), 1000); // never hang the prompt
  });
}

// ms -> "6m 12s" or "1h 30m"
function fmtDur(ms) {
  const s = Math.floor((ms || 0) / 1000);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  return h ? `${h}h ${m}m` : `${m}m ${sec}s`;
}

function contextPct(cw) {
  let pct = cw.used_percentage;
  if (pct == null && cw.current_usage) {
    const u = cw.current_usage;
    const used =
      (u.input_tokens || 0) +
      (u.cache_creation_input_tokens || 0) +
      (u.cache_read_input_tokens || 0);
    const size = cw.context_window_size || 200000;
    pct = size ? (used / size) * 100 : 0;
  }
  return Math.max(0, Math.min(100, Math.floor(pct || 0)));
}

function gauge(pct, color, width = 14) {
  const filled = Math.round((pct / 100) * width);
  return fg(color, "▰".repeat(filled)) + track("▱".repeat(width - filled));
}

(async () => {
  let info = {};
  try {
    info = JSON.parse((await readStdin()) || "{}");
  } catch {
    info = {};
  }

  // ---- Line 1: model · uptime ----
  const line1 = [];
  const model = info.model && info.model.display_name;
  if (model) line1.push("🤖 " + neon(bold(model.toUpperCase())));

  // effort.level is absent when the model lacks reasoning effort support
  const effort = info.effort && info.effort.level;
  if (effort) {
    const ec = EFFORT_COLOR[effort] || 51;
    line1.push("⚡ " + steel("EFFORT ") + fg(ec, bold(effort.toUpperCase())));
  }

  const cost = info.cost || {};
  if (cost.total_duration_ms) {
    line1.push(
      "⏱ " + steel("UPTIME ") + fg(80, fmtDur(cost.total_duration_ms))
    );
  }

  // ---- Line 2: context gauge (full width) ----
  const cw = info.context_window || {};
  const pct = contextPct(cw);
  const tc = band(pct);
  let ctx =
    "🧠 " + steel("CONTEXT ") + gauge(pct, tc) + " " + fg(tc, bold(`${pct}%`));
  if (pct >= 30) ctx += " 🔥";
  if (info.exceeds_200k_tokens) ctx += " " + fg(CRIT, bold("⚠ OVER 200K"));

  process.stdout.write(line1.join(SEP) + "\n" + ctx);
})();
