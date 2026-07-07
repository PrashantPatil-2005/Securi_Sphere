/**
 * Securi k6 smoke load test.
 *
 * Exercises health checks and authenticated read APIs at low concurrency.
 * Intended for CI gates — not a full capacity benchmark.
 *
 * Env:
 *   BASE_URL          API base (default http://localhost:8000)
 *   LOADTEST_EMAIL    Login email (default loadtest@ci.local)
 *   LOADTEST_PASSWORD Login password (default testpass123)
 */

import http from "k6/http";
import { check, sleep } from "k6";

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";
const EMAIL = __ENV.LOADTEST_EMAIL || "loadtest@ci.local";
const PASSWORD = __ENV.LOADTEST_PASSWORD || "testpass123";

export const options = {
  scenarios: {
    smoke: {
      executor: "constant-vus",
      vus: 5,
      duration: "30s",
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.05"],
    http_req_duration: ["p(95)<800"],
    checks: ["rate>0.95"],
  },
};

function jsonHeaders(token) {
  const headers = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  return { headers };
}

export function setup() {
  const register = http.post(
    `${BASE_URL}/api/v1/auth/register`,
    JSON.stringify({ email: EMAIL, password: PASSWORD }),
    jsonHeaders(null),
  );

  if (register.status !== 200 && register.status !== 400) {
    throw new Error(`register failed: ${register.status} ${register.body}`);
  }

  const login = http.post(
    `${BASE_URL}/api/v1/auth/login`,
    JSON.stringify({ email: EMAIL, password: PASSWORD }),
    jsonHeaders(null),
  );

  if (login.status !== 200) {
    throw new Error(`login failed: ${login.status} ${login.body}`);
  }

  const token = login.json("access_token");
  if (!token) {
    throw new Error("login response missing access_token");
  }

  return { token };
}

export default function (data) {
  const auth = jsonHeaders(data.token);

  const health = http.get(`${BASE_URL}/health`);
  check(health, { "health 200": (r) => r.status === 200 });

  const ready = http.get(`${BASE_URL}/health/ready`);
  check(ready, { "ready 200": (r) => r.status === 200 });

  const overview = http.get(`${BASE_URL}/api/v1/overview`, auth);
  check(overview, { "overview 200": (r) => r.status === 200 });

  const alerts = http.get(`${BASE_URL}/api/v1/alerts?page_size=10`, auth);
  check(alerts, { "alerts 200": (r) => r.status === 200 });

  const events = http.get(`${BASE_URL}/api/v1/events?page_size=10`, auth);
  check(events, { "events 200": (r) => r.status === 200 });

  const hosts = http.get(`${BASE_URL}/api/v1/hosts`, auth);
  check(hosts, { "hosts 200": (r) => r.status === 200 });

  const siem = http.get(`${BASE_URL}/api/v1/search/siem?q=severity:medium`, auth);
  check(siem, { "siem search 200": (r) => r.status === 200 });

  const offenses = http.get(`${BASE_URL}/api/v1/offenses?page_size=5`, auth);
  check(offenses, { "offenses 200": (r) => r.status === 200 });

  const playbooks = http.get(`${BASE_URL}/api/v1/playbooks`, auth);
  check(playbooks, { "playbooks 200": (r) => r.status === 200 });

  const ueba = http.get(`${BASE_URL}/api/v1/ueba/summary`, auth);
  check(ueba, { "ueba summary 200": (r) => r.status === 200 });

  const notifications = http.get(`${BASE_URL}/api/v1/notifications/unread-count`, auth);
  check(notifications, { "notifications 200": (r) => r.status === 200 });

  const mitre = http.get(`${BASE_URL}/api/v1/mitre/matrix?preset=24h`, auth);
  check(mitre, { "mitre matrix 200": (r) => r.status === 200 });

  const mitreDrill = http.get(`${BASE_URL}/api/v1/mitre/techniques/T1110/drilldown?preset=24h`, auth);
  check(mitreDrill, { "mitre drilldown 200": (r) => r.status === 200 });

  const savedSearches = http.get(`${BASE_URL}/api/v1/saved-searches`, auth);
  check(savedSearches, { "saved searches 200": (r) => r.status === 200 });

  const dashboardLayout = http.get(`${BASE_URL}/api/v1/dashboard/layout`, auth);
  check(dashboardLayout, { "dashboard layout 200": (r) => r.status === 200 });

  const timelines = http.get(`${BASE_URL}/api/v1/timelines?page_size=5&preset=24h`, auth);
  check(timelines, { "timelines 200": (r) => r.status === 200 });

  const riskTrends = http.get(`${BASE_URL}/api/v1/siem/risk-score-trends?preset=7d`, auth);
  check(riskTrends, { "risk score trends 200": (r) => r.status === 200 });

  const deliveryTest = http.post(
    `${BASE_URL}/api/v1/notifications/settings/test`,
    JSON.stringify({
      channels: { email: true, slack: false, telegram: false },
      email_enabled: true,
      email_address: "smoke@example.com",
    }),
    auth,
  );
  check(deliveryTest, { "delivery test 200": (r) => r.status === 200 });

  const mfaStatus = http.get(`${BASE_URL}/api/v1/auth/mfa/status`, auth);
  check(mfaStatus, { "mfa status 200": (r) => r.status === 200 });

  const auditExport = http.get(`${BASE_URL}/api/v1/audit/export?format=json&limit=5`, auth);
  check(auditExport, { "audit export 200": (r) => r.status === 200 });

  const auditIntegrity = http.get(`${BASE_URL}/api/v1/audit/integrity?limit=100`, auth);
  check(auditIntegrity, { "audit integrity 200": (r) => r.status === 200 });

  const backups = http.get(`${BASE_URL}/api/v1/backups`, auth);
  check(backups, { "backups 200": (r) => r.status === 200 });

  sleep(0.3);
}
