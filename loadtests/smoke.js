/**
 * SecuriSphere k6 smoke load test.
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

  const notifications = http.get(`${BASE_URL}/api/v1/notifications/unread-count`, auth);
  check(notifications, { "notifications 200": (r) => r.status === 200 });

  sleep(0.3);
}
