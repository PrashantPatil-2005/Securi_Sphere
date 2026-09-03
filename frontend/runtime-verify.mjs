/**
 * Runtime performance verification against the real frontend (dev mode).
 *
 * Measures:
 *   1. Backend liveness (/docs only — root 404 is expected, no code change)
 *   2. /login initial HTTP request count + API timings
 *   3. Login flow timing
 *   4. Dashboard initial HTTP request count (onboarding default state)
 *   5. Onboarding requests after wizard dismissal (expect 0)
 *   6. WebSocket traffic (connect, auth, frames)
 *   7. WS-triggered HTTP requests over ~30s with a live simulation
 *   8. API timings per endpoint
 *   9. UI responsiveness (long tasks, paints, navigation timing)
 *  10. Console/runtime errors
 *  11. Real-data verification (API values vs DOM)
 *
 * Usage: node frontend/runtime-verify.mjs   (from project root)
 */
import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";

const FRONTEND = "http://localhost:3000";
const BACKEND = "http://127.0.0.1:8000";
const OBSERVE_MS = 30_000;
const FLUSH_GAP_MS = 1200;

// ---------- env ----------
function loadEnv(file) {
  const out = {};
  if (!fs.existsSync(file)) return out;
  for (const line of fs.readFileSync(file, "utf8").split(/\r?\n/)) {
    const m = line.match(/^([A-Za-z_][A-Za-z0-9_]*)=(.*)$/);
    if (m) out[m[1]] = m[2];
  }
  return out;
}
const backendEnv = loadEnv(path.resolve("backend/.env"));
const EMAIL = "admin@test.local";
const PASSWORD = backendEnv.DEV_USER_PASSWORD;
if (!PASSWORD) {
  console.error("DEV_USER_PASSWORD missing from backend/.env — cannot log in.");
  process.exit(1);
}

// ---------- collectors ----------
function createCollectors(page) {
  const state = { requests: [], console: [], pageErrors: [], failed: [], ws: [] };
  const reqMap = new Map();
  const now = () => Date.now();

  page.on("request", (r) => {
    const entry = {
      url: r.url(),
      method: r.method(),
      type: r.resourceType(),
      start: now(),
      end: null,
      status: null,
      failed: false,
      path: r.url().replace(/^https?:\/\/[^/]+/, "").split("?")[0],
      query: r.url().split("?")[1] || "",
    };
    reqMap.set(r, entry);
    state.requests.push(entry);
  });
  page.on("response", (res) => {
    const entry = reqMap.get(res.request());
    if (entry) {
      entry.end = now();
      entry.status = res.status();
    }
  });
  page.on("requestfailed", (r) => {
    const entry = reqMap.get(r);
    if (entry) {
      entry.failed = true;
      entry.end = entry.end ?? now();
      state.failed.push({ url: r.url(), error: r.failure()?.errorText });
    }
  });
  page.on("console", (m) => {
    if (m.type() === "error" || m.type() === "warning") {
      state.console.push({ type: m.type(), text: m.text().slice(0, 500) });
    }
  });
  page.on("pageerror", (e) => state.pageErrors.push(String(e).slice(0, 500)));
  page.on("websocket", (ws) => {
    const isApi = ws.url().includes("/api/v1/ws");
    state.ws.push({ kind: "open", url: ws.url(), t: now(), data: null });
    if (!isApi) return; // ignore Next.js HMR sockets for traffic stats
    ws.on("framesent", (f) => {
      state.ws.push({ kind: "send", url: ws.url(), t: now(), data: String(f.payload) });
    });
    ws.on("framereceived", (f) => {
      state.ws.push({ kind: "recv", url: ws.url(), t: now(), data: String(f.payload) });
    });
    ws.on("close", () => state.ws.push({ kind: "close", url: ws.url(), t: now(), data: null }));
    ws.on("socketerror", () => state.ws.push({ kind: "error", url: ws.url(), t: now(), data: null }));
  });
  return state;
}

const fmt = (ms) => (ms == null ? "-" : `${ms.toFixed(0)}ms`);

function apiStats(requests, since = 0) {
  const byPath = {};
  for (const r of requests) {
    if (r.start < since) continue;
    if (!r.url.includes("/api/")) continue;
    const key = `${r.method !== "GET" ? r.method + " " : ""}${r.path}${r.query ? "?" + r.query : ""}`;
    const dur = r.end ? r.end - r.start : null;
    const rec = (byPath[key] ||= { count: 0, times: [], statuses: {}, lastStart: r.start });
    rec.count++;
    if (dur != null) rec.times.push(dur);
    rec.statuses[r.status ?? "?"] = (rec.statuses[r.status ?? "?"] || 0) + 1;
    rec.lastStart = Math.max(rec.lastStart, r.start);
  }
  const rows = Object.entries(byPath).map(([path, rec]) => {
    const t = rec.times;
    const sum = t.reduce((a, b) => a + b, 0);
    return {
      path,
      count: rec.count,
      avg: t.length ? sum / t.length : null,
      min: t.length ? Math.min(...t) : null,
      max: t.length ? Math.max(...t) : null,
      statuses: rec.statuses,
    };
  });
  rows.sort((a, b) => b.count - a.count || (a.avg ?? 0) - (b.avg ?? 0));
  return rows;
}

function countRequests(requests, since, opts = {}) {
  const apiOnly = opts.apiOnly ?? false;
  return requests.filter((r) => {
    if (r.start < since) return false;
    if (r.failed && !opts.includeFailed) return false;
    if (apiOnly) return r.url.includes("/api/");
    return true;
  }).length;
}

const ONBOARDING_MARKERS = [
  "/api/v1/overview",
  "/api/v1/simulation/runs?page_size=1",
  "/api/v1/alerts?status=investigating&page_size=1",
  "/api/v1/alerts?status=resolved&page_size=1",
  "/api/v1/offenses?page_size=1",
  "/api/v1/incidents?page_size=1",
  "/api/v1/notifications/settings",
];

function countOnboarding(requests, since) {
  return requests.filter(
    (r) =>
      r.start >= since &&
      !r.failed &&
      ONBOARDING_MARKERS.some((m) => r.url.includes(m.replace("/api/v1/", "")) && r.url.includes("/api/v1/")),
  ).length;
}

function onboardingDetail(requests, since) {
  return ONBOARDING_MARKERS.map((m) => {
    const hit = requests.filter((r) => r.start >= since && r.url.includes(m));
    return { marker: m, count: hit.length, statuses: hit.map((h) => h.status) };
  });
}

function wsTraffic(state, since) {
  const recv = state.ws.filter((w) => w.kind === "recv" && w.t >= since);
  const sent = state.ws.filter((w) => w.kind === "send" && w.t >= since);
  const byType = {};
  for (const w of recv) {
    try {
      const parsed = JSON.parse(w.data);
      byType[parsed.type] = (byType[parsed.type] || 0) + 1;
    } catch {
      byType["(non-json)"] = (byType["(non-json)"] || 0) + 1;
    }
  }
  return { recv: recv.length, sent: sent.length, byType };
}

function flushAnalysis(requests, since, until) {
  const api = requests
    .filter((r) => r.method === "GET" && r.url.includes("/api/") && r.start >= since && r.start <= until && !r.failed)
    .sort((a, b) => a.start - b.start);
  if (api.length === 0) return { flushes: [], total: 0 };
  const flushes = [];
  let cur = { start: api[0].start, items: [api[0]] };
  for (let i = 1; i < api.length; i++) {
    if (api[i].start - api[i - 1].start > FLUSH_GAP_MS) {
      flushes.push(cur);
      cur = { start: api[i].start, items: [api[i]] };
    } else {
      cur.items.push(api[i]);
    }
  }
  flushes.push(cur);
  return {
    total: api.length,
    flushes: flushes.map((f) => ({
      startMs: Math.round(f.start - since),
      n: f.items.length,
      paths: [...new Set(f.items.map((i) => i.path + (i.query ? "?" + i.query : "")))],
    })),
  };
}

// ---------- main ----------
const report = [];
const log = (...a) => {
  const line = a.join(" ");
  console.log(line);
  report.push(line);
};
const section = (t) => {
  log("");
  log("=".repeat(72));
  log(t);
  log("=".repeat(72));
};

async function main() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });

  // UI responsiveness instrumentation (long tasks + paint timings)
  await context.addInitScript(() => {
    window.__longTasks = [];
    window.__paints = [];
    try {
      new PerformanceObserver((l) => {
        for (const e of l.getEntries()) {
          window.__longTasks.push({ start: Math.round(e.startTime), dur: Math.round(e.duration) });
        }
      }).observe({ entryTypes: ["longtask"] });
      new PerformanceObserver((l) => {
        for (const e of l.getEntries()) window.__paints.push({ name: e.name, t: Math.round(e.startTime) });
      }).observe({ entryTypes: ["paint"] });
    } catch (e) {
      /* older engine */
    }
  });

  const page = await context.newPage();
  const st = createCollectors(page);

  // ---------------------------------------------------------------- phase 1
  section("1. Backend liveness (docs only)");
  for (const p of ["/docs", "/openapi.json", "/"]) {
    try {
      const res = await fetch(BACKEND + p, { method: "GET" });
      log(`  ${p} -> ${res.status} (expected: /docs 200, / 404 is OK — no root route, no fix applied)`);
    } catch (e) {
      log(`  ${p} -> ERROR ${e.message}`);
    }
  }

  // ---------------------------------------------------------------- phase 2
  section("2. /login initial load");
  st.requests.length = 0;
  const loginNavStart = Date.now();
  await page.goto(FRONTEND + "/login", { waitUntil: "load" });
  await page.waitForTimeout(1200); // let settings/public + auth/me settle
  const loginNavEnd = Date.now();
  const loginTotal = countRequests(st.requests, loginNavStart);
  const loginApi = countRequests(st.requests, loginNavStart, { apiOnly: true });
  log(`  Navigation start -> load: ${fmt(loginNavEnd - loginNavStart)}`);
  log(`  Total HTTP requests: ${loginTotal}`);
  log(`  API requests: ${loginApi}`);
  for (const r of apiStats(st.requests, loginNavStart)) {
    log(`    ${r.path} x${r.count}  avg ${fmt(r.avg)}  (min ${fmt(r.min)} / max ${fmt(r.max)})  ${JSON.stringify(r.statuses)}`);
  }
  const loginTiming = await page.evaluate(() => {
    const n = performance.getEntriesByType("navigation")[0];
    return n ? { ttfb: Math.round(n.responseStart), dom: Math.round(n.domContentLoadedEventEnd), load: Math.round(n.loadEventEnd) } : null;
  });
  if (loginTiming) log(`  navigation timing: TTFB ${fmt(loginTiming.ttfb)}, DOMContentLoaded ${fmt(loginTiming.dom)}, load ${fmt(loginTiming.load)}`);

  // ---------------------------------------------------------------- phase 3
  section("3. Login flow timing");
  const submitStart = Date.now();
  await page.fill('input[type="email"]', EMAIL);
  await page.fill("#password", PASSWORD);
  await page.click('button[type="submit"]');
  await page.waitForURL((u) => u.pathname === "/", { timeout: 20000 });
  const urlChanged = Date.now();
  log(`  Submit -> dashboard URL: ${fmt(urlChanged - submitStart)}`);
  // wait for content + settle
  await page.waitForSelector("text=Security Operations", { timeout: 20000 });
  const contentShown = Date.now();
  log(`  URL change -> 'Security Operations' rendered: ${fmt(contentShown - urlChanged)}`);
  await page.waitForTimeout(3500); // let all React Query initial fetches + onboarding finish
  const dashboardSettled = Date.now();

  // ---------------------------------------------------------------- phase 4
  section("4. Dashboard initial load (onboarding wizard shown — default)");
  const dashTotal = countRequests(st.requests, submitStart);
  const dashApi = countRequests(st.requests, submitStart, { apiOnly: true });
  log(`  HTTP requests since login submit: ${dashTotal} total / ${dashApi} API`);
  for (const r of apiStats(st.requests, submitStart)) {
    log(`    ${r.path}${r.query ? "?" + r.query : ""} x${r.count}  avg ${fmt(r.avg)}  (min ${fmt(r.min)} / max ${fmt(r.max)})`);
  }
  log(`  Onboarding requests (default, wizard visible): ${countOnboarding(st.requests, submitStart)}`);
  for (const d of onboardingDetail(st.requests, submitStart)) {
    log(`    ${d.marker} -> ${d.count}x ${JSON.stringify(d.statuses)}`);
  }

  // WebSocket state after login
  await page.waitForTimeout(1000);
  const wsConn = st.ws.filter((w) => w.kind === "open" && w.url.includes("/api/v1/ws"));
  const wsAuth = st.ws.filter((w) => w.kind === "send" && w.data.includes("auth"));
  log(`  WebSocket: ${wsConn.length} connection(s), auth frame sent: ${wsAuth.length > 0 ? "yes" : "NO"}`);

  // ---------------------------------------------------------------- phase 5
  section("5. Onboarding after wizard dismissal (localStorage set + reload)");
  await page.evaluate(() => localStorage.setItem("securi_onboarding_wizard_done", "1"));
  st.requests.length = 0;
  const reloadStart = Date.now();
  await page.reload({ waitUntil: "load" });
  await page.waitForSelector("text=Security Operations", { timeout: 20000 });
  await page.waitForTimeout(3000);
  const onboardingAfter = countOnboarding(st.requests, reloadStart);
  log(`  Onboarding requests after dismissal: ${onboardingAfter}`);
  for (const d of onboardingDetail(st.requests, reloadStart)) log(`    ${d.marker} -> ${d.count}x`);
  // restore wizard for later phases (doesn't matter for measurement)
  await page.evaluate(() => localStorage.removeItem("securi_onboarding_wizard_done"));

  // ---------------------------------------------------------------- phase 6/7
  section("6. Baseline WebSocket idle observation (10s)");
  const wsSince = Date.now();
  st.ws = st.ws.filter((w) => w.t >= wsSince - 1000); // keep recent socket lifecycle
  await page.waitForTimeout(10_000);
  const idleWs = wsTraffic(st, wsSince);
  const idleApi = countRequests(st.requests, wsSince, { apiOnly: true });
  log(`  WS frames received: ${idleWs.recv}, sent: ${idleWs.sent}`);
  log(`  WS message types: ${JSON.stringify(idleWs.byType)}`);
  log(`  API requests during idle 10s: ${idleApi}`);

  section("7. WS-triggered HTTP requests over ~30s (simulation-driven)");
  // pick a host
  const hosts = await page.evaluate(async () => {
    const r = await fetch("/api/v1/hosts?page_size=5", { credentials: "include" });
    return r.json();
  });
  let hostId = hosts?.items?.[0]?.id || null;
  if (!hostId) {
    log("  No hosts found — creating a verification host…");
    const created = await page.evaluate(async () => {
      const r = await fetch("/api/v1/hosts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ name: "perf-verify-host" }),
      });
      return r.json();
    });
    hostId = created?.id;
    if (!hostId) {
      log("  ERROR: could not create host for simulation");
      hostId = null;
    }
  }
  if (hostId) log(`  Using host ${hostId}`);

  // scenario ids
  const scenarios = await page.evaluate(async () => {
    const r = await fetch("/api/v1/simulation/scenarios", { credentials: "include" });
    return r.json();
  });
  const ids = (scenarios?.scenarios || []).map((s) => s.id);
  const bruteId = ids.find((i) => /brute/.test(i));
  const healthId = ids.find((i) => /host.*health|health.*crisis/.test(i)) || ids.find((i) => /health/.test(i));
  log(`  Available scenarios: ${JSON.stringify(ids)}`);

  const obsSince = Date.now();
  st.requests.length = 0; // reset request log for the observation window

  if (hostId && bruteId) {
    await page.evaluate(
      ({ scenario, hid }) => {
        fetch(`/api/v1/simulation/run/${scenario}?host_id=${hid}`, { method: "POST", credentials: "include" }).catch(() => {});
      },
      { scenario: bruteId, hid: hostId },
    );
    log(`  Started '${bruteId}' at t=0`);
  } else {
    log("  WARN: no brute-force scenario or host — observing idle WS only");
  }

  await page.waitForTimeout(15_000);
  if (hostId && healthId) {
    await page.evaluate(
      ({ scenario, hid }) => {
        fetch(`/api/v1/simulation/run/${scenario}?host_id=${hid}`, { method: "POST", credentials: "include" }).catch(() => {});
      },
      { scenario: healthId, hid: hostId },
    );
    log(`  Started '${healthId}' at t=15s`);
  }

  await page.waitForTimeout(OBSERVE_MS - 15_000);
  const obsEnd = Date.now();
  const obsDur = obsEnd - obsSince;

  const wsObs = wsTraffic(st, obsSince);
  log(`\n  Observation window: ${(obsDur / 1000).toFixed(1)}s`);
  log(`  WS frames received: ${wsObs.recv} | sent: ${wsObs.sent}`);
  log(`  WS message types: ${JSON.stringify(wsObs.byType)}`);
  const flush = flushAnalysis(st.requests, obsSince, obsEnd);
  log(`  API HTTP requests during window: ${flush.total}`);
  log(`  Invalidation flush cycles (gap > ${FLUSH_GAP_MS}ms): ${flush.flushes.length}`);
  for (const f of flush.flushes) {
    log(`    t=${f.startMs}ms  ${f.n} request(s): ${f.paths.join(", ")}`);
  }
  // per-5s buckets
  log("  Traffic per 5s bucket:");
  for (let t = 0; t < obsDur; t += 5000) {
    const tEnd = t + 5000;
    const wsN = st.ws.filter((w) => w.kind === "recv" && w.t >= obsSince + t && w.t < obsSince + tEnd).length;
    const apiN = st.requests.filter((r) => r.method === "GET" && r.url.includes("/api/") && r.start >= obsSince + t && r.start < obsSince + tEnd).length;
    log(`    ${(t / 1000).toFixed(0)}-${(Math.min(tEnd, obsDur) / 1000).toFixed(0)}s  WS recv: ${wsN}  API reqs: ${apiN}`);
  }

  // ---------------------------------------------------------------- phase 8
  section("8. API timings (whole session, unique paths)");
  for (const r of apiStats(st.requests, 0)) {
    log(`  ${r.path}${r.query ? "?" + r.query : ""} x${r.count}  avg ${fmt(r.avg)}  min ${fmt(r.min)}  max ${fmt(r.max)}  ${JSON.stringify(r.statuses)}`);
  }

  // ---------------------------------------------------------------- phase 9
  section("9. UI responsiveness");
  const perf = await page.evaluate(() => {
    const lt = window.__longTasks || [];
    const paints = window.__paints || [];
    const total = lt.reduce((a, b) => a + b.dur, 0);
    return {
      longTasks: lt.length,
      totalBlockedMs: total,
      maxLongTaskMs: lt.reduce((m, t) => Math.max(m, t.dur), 0),
      paints,
      lt,
    };
  });
  log(`  Long tasks (>50ms main-thread blocks): ${perf.longTasks}, total ${fmt(perf.totalBlockedMs)}, worst ${fmt(perf.maxLongTaskMs)}`);
  for (const lt of perf.lt) log(`    t=${lt.start}ms  dur=${lt.dur}ms`);
  log(`  Paint timings: ${perf.paints.map((p) => `${p.name}@${p.t}ms`).join(", ") || "none captured"}`);
  // live feed status + connection banner state
  const feedText = await page.locator("text=Live feed:").first().textContent().catch(() => "n/a");
  log(`  Live feed status: ${feedText?.trim()}`);

  // ---------------------------------------------------------------- phase 10
  section("10. Console / runtime errors");
  const errs = {};
  for (const c of st.console) {
    const key = `${c.type}: ${c.text}`;
    errs[key] = (errs[key] || 0) + 1;
  }
  log(`  Console errors/warnings: ${st.console.length}`);
  for (const [k, v] of Object.entries(errs)) log(`    [${v}x] ${k.slice(0, 300)}`);
  log(`  Uncaught page errors: ${st.pageErrors.length}`);
  for (const e of st.pageErrors) log(`    ${e.slice(0, 300)}`);
  log(`  Failed requests: ${st.failed.length}`);
  for (const f of st.failed) log(`    ${f.url} -> ${f.error}`);
  const httpErrs = {};
  for (const r of st.requests) {
    if (r.url.includes("/api/") && r.status && r.status >= 400) {
      const k = `${r.status} ${r.path}`;
      httpErrs[k] = (httpErrs[k] || 0) + 1;
    }
  }
  log(`  HTTP >=400 API responses: ${Object.keys(httpErrs).length ? "" : "none"}`);
  for (const [k, v] of Object.entries(httpErrs)) log(`    [${v}x] ${k}`);
  log("  (401 on /auth/me before login is expected — the login page probes session state)");

  // ---------------------------------------------------------------- phase 11
  section("11. Real-data verification (API vs rendered DOM)");
  const data = await page.evaluate(async () => {
    const get = async (p) => {
      const r = await fetch(p, { credentials: "include" });
      return { status: r.status, body: await r.json().catch(() => null) };
    };
    return {
      executive: await get("/api/v1/siem/executive"),
      severity: await get("/api/v1/siem/severity-distribution"),
      trend: await get("/api/v1/siem/events-trend"),
      hosts: await get("/api/v1/siem/top-risky-hosts"),
      health: await get("/api/v1/system/health"),
    };
  });
  const exec = data.executive.body;
  if (exec) {
    log(`  /siem/executive: ${JSON.stringify(exec)}`);
  } else {
    log(`  /siem/executive: HTTP ${data.executive.status} — no body`);
  }
  if (data.severity.body) log(`  /siem/severity-distribution: ${JSON.stringify(data.severity.body).slice(0, 400)}`);
  if (data.trend.body) log(`  /siem/events-trend: ${JSON.stringify(data.trend.body).slice(0, 400)}`);
  if (data.hosts.body) log(`  /siem/top-risky-hosts: ${JSON.stringify(data.hosts.body).slice(0, 400)}`);
  if (data.health.body) log(`  /system/health: ${JSON.stringify(data.health.body)}`);

  // DOM KPI values vs API
  const kpiDom = await page.evaluate(() => {
    const out = [];
    const cards = document.querySelectorAll(".kpi-card");
    for (const c of cards) out.push(c.textContent.replace(/\s+/g, " ").trim());
    return out.slice(0, 12);
  });
  log(`  KPI cards in DOM: ${JSON.stringify(kpiDom)}`);

  // check for error/empty states in main dashboard
  const dashText = await page.evaluate(() => document.body.innerText);
  const errState = ["Failed to load metrics", "Failed to load", "ErrorState"].filter((s) => dashText.includes(s));
  log(`  Dashboard error-state markers: ${errState.length ? errState.join(", ") : "none"}`);

  await browser.close();

  // ---------------------------------------------------------------- report
  const reportText = report.join("\n");
  const outPath = path.resolve("docs/runtime-performance-verification-report.md");
  fs.writeFileSync(
    outPath,
    `# Runtime Performance Verification Report (Real Frontend)\n\n**Date:** September 3, 2026\n**Method:** Headless Chromium driving the live dev frontend (http://localhost:3000) against the running backend (http://127.0.0.1:8000, proxied via Next.js rewrites). No code changes; backend root 404 intentionally left untouched.\n\n\`\`\`\n${reportText}\n\`\`\`\n`,
  );
  console.log(`\nReport written to ${outPath}`);
}

main().catch((e) => {
  console.error("SCRIPT FAILED:", e);
  process.exit(1);
});