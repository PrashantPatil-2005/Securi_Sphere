"""Securi_Sphere Performance & Load Test Suite.

Measures real system behavior under load. Not synthetic benchmarks.
Every number comes from an actual HTTP request against a real backend.

Usage:
    python -m tests.perf.run_perf
    python -m tests.perf.run_perf --profile=light
    python -m tests.perf.run_perf --profile=normal
    python -m tests.perf.run_perf --profile=heavy
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

BASE_URL = "http://127.0.0.1:8000"


@dataclass
class RequestResult:
    status: int
    latency_ms: float
    body_bytes: int = 0
    error: str | None = None


@dataclass
class BenchmarkResult:
    name: str
    results: list[RequestResult] = field(default_factory=list)
    start_time: float = 0.0
    end_time: float = 0.0

    @property
    def count(self) -> int:
        return len(self.results)

    @property
    def errors(self) -> int:
        return sum(1 for r in self.results if r.error or r.status >= 400)

    @property
    def error_rate(self) -> float:
        return (self.errors / self.count * 100) if self.count else 0

    @property
    def latencies(self) -> list[float]:
        return [r.latency_ms for r in self.results if not r.error]

    @property
    def p50(self) -> float:
        lat = self.latencies
        return sorted(lat)[len(lat) // 2] if lat else 0

    @property
    def p95(self) -> float:
        lat = sorted(self.latencies)
        idx = int(len(lat) * 0.95)
        return lat[min(idx, len(lat) - 1)] if lat else 0

    @property
    def p99(self) -> float:
        lat = sorted(self.latencies)
        idx = int(len(lat) * 0.99)
        return lat[min(idx, len(lat) - 1)] if lat else 0

    @property
    def min_latency(self) -> float:
        lat = self.latencies
        return min(lat) if lat else 0

    @property
    def max_latency(self) -> float:
        lat = self.latencies
        return max(lat) if lat else 0

    @property
    def mean_latency(self) -> float:
        lat = self.latencies
        return statistics.mean(lat) if lat else 0

    @property
    def duration_s(self) -> float:
        return self.end_time - self.start_time

    @property
    def throughput(self) -> float:
        return self.count / self.duration_s if self.duration_s > 0 else 0

    @property
    def total_body_bytes(self) -> int:
        return sum(r.body_bytes for r in self.results)

    def summary(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "count": self.count,
            "errors": self.errors,
            "error_rate_pct": round(self.error_rate, 2),
            "duration_s": round(self.duration_s, 3),
            "throughput_rps": round(self.throughput, 1),
            "latency_ms": {
                "min": round(self.min_latency, 1),
                "p50": round(self.p50, 1),
                "p95": round(self.p95, 1),
                "p99": round(self.p99, 1),
                "max": round(self.max_latency, 1),
                "mean": round(self.mean_latency, 1),
            },
            "total_body_bytes": self.total_body_bytes,
        }


async def single_request(
    client: httpx.AsyncClient, method: str, path: str, **kwargs: Any
) -> RequestResult:
    start = time.monotonic()
    try:
        r = await client.request(method, path, **kwargs)
        elapsed = (time.monotonic() - start) * 1000
        return RequestResult(
            status=r.status_code,
            latency_ms=elapsed,
            body_bytes=len(r.content),
        )
    except Exception as e:
        elapsed = (time.monotonic() - start) * 1000
        return RequestResult(status=0, latency_ms=elapsed, error=str(e))


async def run_sequential(
    client: httpx.AsyncClient,
    name: str,
    method: str,
    path: str,
    count: int = 100,
    **kwargs: Any,
) -> BenchmarkResult:
    bench = BenchmarkResult(name=name)
    bench.start_time = time.monotonic()
    for _ in range(count):
        bench.results.append(await single_request(client, method, path, **kwargs))
    bench.end_time = time.monotonic()
    return bench


async def run_concurrent(
    client: httpx.AsyncClient,
    name: str,
    method: str,
    path: str,
    concurrency: int = 10,
    total: int = 100,
    **kwargs: Any,
) -> BenchmarkResult:
    bench = BenchmarkResult(name=name)
    sem = asyncio.Semaphore(concurrency)

    async def _do():
        async with sem:
            bench.results.append(await single_request(client, method, path, **kwargs))

    bench.start_time = time.monotonic()
    await asyncio.gather(*[_do() for _ in range(total)])
    bench.end_time = time.monotonic()
    return bench


async def run_concurrent_with_body(
    client: httpx.AsyncClient,
    name: str,
    method: str,
    path: str,
    bodies: list[dict],
    concurrency: int = 10,
    headers: dict | None = None,
) -> BenchmarkResult:
    bench = BenchmarkResult(name=name)
    sem = asyncio.Semaphore(concurrency)

    async def _do(body: dict):
        async with sem:
            bench.results.append(
                await single_request(client, method, path, json=body, headers=headers or {})
            )

    bench.start_time = time.monotonic()
    await asyncio.gather(*[_do(b) for b in bodies])
    bench.end_time = time.monotonic()
    return bench


def make_event(i: int, source: str = "perf-test") -> dict:
    return {
        "event_type": "ssh_login_success",
        "severity": "low",
        "source": source,
        "description": f"Perf test event {i}",
        "raw_log": f"Accepted password for user{i} from 10.0.{i % 256}.{i % 256}",
        "timestamp": "2026-08-31T12:00:00Z",
        "metadata_": {"perf_index": i, "batch": True},
    }


async def get_auth_headers(client: httpx.AsyncClient) -> dict[str, str]:
    r = await client.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"email": "admin@test.local", "password": "testpass123"},
    )
    if r.status_code != 200:
        raise RuntimeError(f"Login failed: {r.status_code} {r.text[:200]}")
    data = r.json()
    token = data.get("access_token") or data.get("token", "")
    return {"Authorization": f"Bearer {token}"}


async def get_agent_api_key(client: httpx.AsyncClient, user_headers: dict[str, str]) -> str:
    """Provision a test agent and return its API key for ingestion benchmarks."""
    import uuid
    unique = uuid.uuid4().hex[:8]

    # Create host
    r1 = await client.post(
        f"{BASE_URL}/api/v1/hosts",
        json={"name": f"perf-agent-{unique}", "os": "linux"},
        headers=user_headers,
    )
    if r1.status_code not in (200, 201):
        raise RuntimeError(f"Host create failed: {r1.status_code} {r1.text[:200]}")
    host_id = r1.json()["id"]

    # Create enrollment token
    r2 = await client.post(
        f"{BASE_URL}/api/v1/hosts/{host_id}/enrollment-token",
        headers=user_headers,
    )
    if r2.status_code not in (200, 201):
        raise RuntimeError(f"Enrollment token failed: {r2.status_code} {r2.text[:200]}")
    enrollment_token = r2.json()["token"]

    # Register agent
    r3 = await client.post(
        f"{BASE_URL}/api/v1/agent/register",
        json={
            "enrollment_token": enrollment_token,
            "hostname": f"perf-agent-{unique}",
            "os": "linux",
            "agent_version": "1.0.0",
            "capabilities": ["events"],
        },
    )
    if r3.status_code not in (200, 201):
        raise RuntimeError(f"Agent register failed: {r3.status_code} {r3.text[:200]}")
    return r3.json()["api_key"]


# ────────────────────────────── Benchmark Sections ──────────────────────────────


async def bench_api_list_endpoints(
    client: httpx.AsyncClient, headers: dict
) -> list[BenchmarkResult]:
    """Benchmark read-heavy API endpoints."""
    endpoints = [
        ("alerts-list", "/api/v1/alerts"),
        ("events-list", "/api/v1/events"),
        ("hosts-list", "/api/v1/hosts"),
        ("offenses-list", "/api/v1/offenses"),
        ("incidents-list", "/api/v1/incidents"),
    ]
    results = []
    for name, path in endpoints:
        r = await run_sequential(
            client, name, "GET", path, count=50, headers=headers
        )
        results.append(r)
    return results


async def bench_dashboard(
    client: httpx.AsyncClient, headers: dict
) -> list[BenchmarkResult]:
    """Benchmark dashboard analytics endpoints."""
    endpoints = [
        ("executive-metrics", "/api/v1/siem/executive"),
        ("severity-distribution", "/api/v1/siem/severity-distribution"),
        ("top-risky-hosts", "/api/v1/siem/top-risky-hosts"),
        ("alert-trends", "/api/v1/siem/events-trend"),
        ("risk-trends", "/api/v1/siem/risk-score-trends"),
        ("mitre-stats", "/api/v1/siem/mitre"),
    ]
    results = []
    for name, path in endpoints:
        r = await run_sequential(
            client, name, "GET", path, count=20, headers=headers
        )
        results.append(r)
    return results


async def bench_concurrent_ingestion(
    client: httpx.AsyncClient, agent_headers: dict, concurrency: int = 10, batch_size: int = 10
) -> BenchmarkResult:
    """Benchmark concurrent event ingestion."""
    bodies = [
        {"events": [make_event(i + j * batch_size) for j in range(batch_size)]}
        for i in range(concurrency * 5)
    ]
    return await run_concurrent_with_body(
        client,
        f"ingestion-c{concurrency}-b{batch_size}",
        "POST",
        "/api/v1/agent/events",
        bodies,
        concurrency=concurrency,
        headers=agent_headers,
    )


async def bench_sequential_ingestion(
    client: httpx.AsyncClient, agent_headers: dict, batch_size: int = 50, count: int = 20
) -> BenchmarkResult:
    """Benchmark sequential ingestion at different batch sizes."""
    body = {"events": [make_event(i) for i in range(batch_size)]}
    return await run_sequential(
        client,
        f"ingestion-seq-b{batch_size}",
        "POST",
        "/api/v1/agent/events",
        count=count,
        json=body,
        headers=agent_headers,
    )


async def bench_alert_mutations(
    client: httpx.AsyncClient, headers: dict
) -> BenchmarkResult:
    """Benchmark alert status changes."""
    r = await client.get(
        f"{BASE_URL}/api/v1/alerts?page_size=10", headers=headers
    )
    if r.status_code != 200:
        return BenchmarkResult(name="alert-mutations (no alerts)")
    alerts = r.json().get("items", r.json().get("alerts", []))
    if not alerts:
        return BenchmarkResult(name="alert-mutations (no alerts)")

    results = []
    bench = BenchmarkResult(name="alert-status-update")
    bench.start_time = time.monotonic()
    for alert in alerts[:5]:
        alert_id = alert.get("id")
        if alert_id:
            res = await single_request(
                client,
                "PATCH",
                f"/api/v1/alerts/{alert_id}",
                headers=headers,
                json={"status": "investigating"},
            )
            results.append(res)
    bench.end_time = time.monotonic()
    bench.results = results
    return bench


async def bench_search(
    client: httpx.AsyncClient, headers: dict
) -> list[BenchmarkResult]:
    """Benchmark search endpoints."""
    queries = [
        ("search-empty", ""),
        ("search-common", "ssh"),
        ("search-selective", "root login failure"),
        ("search-overflow", "*"),
    ]
    results = []
    for name, q in queries:
        params = {"q": q, "page_size": 20} if q else {"page_size": 20}
        r = await run_sequential(
            client,
            name,
            "GET",
            "/api/v1/events",
            count=20,
            headers=headers,
            params=params,
        )
        results.append(r)
    return results


async def bench_report_generation(
    client: httpx.AsyncClient, headers: dict
) -> BenchmarkResult:
    """Benchmark report generation."""
    return await run_sequential(
        client,
        "executive-report",
        "GET",
        "/api/v1/siem/executive",
        count=5,
        headers=headers,
    )


async def bench_concurrent_users(
    client: httpx.AsyncClient, headers: dict, concurrency: int = 10
) -> BenchmarkResult:
    """Benchmark mixed concurrent API traffic simulating multiple users."""
    paths = [
        "/api/v1/alerts?page_size=20",
        "/api/v1/events?page_size=20",
        "/api/v1/hosts?page_size=20",
        "/api/v1/offenses?page_size=20",
        "/api/v1/siem/executive",
    ]
    total_requests = concurrency * 10
    bodies = []
    for i in range(total_requests):
        bodies.append({"_path": paths[i % len(paths)]})

    bench = BenchmarkResult(name=f"concurrent-users-c{concurrency}")
    sem = asyncio.Semaphore(concurrency)

    async def _do(path: str):
        async with sem:
            bench.results.append(
                await single_request(client, "GET", path, headers=headers)
            )

    bench.start_time = time.monotonic()
    await asyncio.gather(
        *[_do(bodies[i]["_path"]) for i in range(total_requests)]
    )
    bench.end_time = time.monotonic()
    return bench


async def bench_backpressure(
    client: httpx.AsyncClient, agent_headers: dict
) -> BenchmarkResult:
    """Test ingestion backpressure under high concurrency."""
    bodies = [
        {"events": [make_event(i) for i in range(10)]} for i in range(200)
    ]
    return await run_concurrent_with_body(
        client,
        "backpressure-c50",
        "POST",
        "/api/v1/agent/events",
        bodies,
        concurrency=50,
        headers=agent_headers,
    )


# ────────────────────────────── Main Runner ──────────────────────────────


async def run_profile(profile: str) -> list[dict]:
    """Run a performance profile and return results."""
    async with httpx.AsyncClient(
        base_url=BASE_URL, timeout=120.0, limits=httpx.Limits(max_connections=100)
    ) as client:
        # Check backend health
        try:
            health = await client.get(f"{BASE_URL}/health/ready")
            if health.status_code != 200:
                print(f"ERROR: Backend not healthy (status={health.status_code})")
                print("Start the backend first: docker compose up -d backend")
                return []
        except httpx.ConnectError:
            print(f"ERROR: Cannot connect to {BASE_URL}")
            print("Start the backend first: docker compose up -d backend")
            return []

        # Authenticate
        print("Authenticating...")
        headers = await get_auth_headers(client)
        print("Authenticated.")

        # Provision agent for ingestion benchmarks
        print("Provisioning test agent...")
        api_key = await get_agent_api_key(client, headers)
        agent_headers = {"X-API-Key": api_key}
        print("Agent ready.\n")

        all_results: list[dict] = []

        print(f"{'='*70}")
        print(f"  SECURI_SPHERE PERFORMANCE TEST — Profile: {profile.upper()}")
        print(f"{'='*70}\n")

        # 1. API List Endpoints
        print(">> API List Endpoints...")
        api_results = await bench_api_list_endpoints(client, headers)
        for r in api_results:
            s = r.summary()
            print(
                f"  {s['name']:30s} | {s['count']:4d} req | "
                f"p50={s['latency_ms']['p50']:7.1f}ms | p95={s['latency_ms']['p95']:7.1f}ms | "
                f"err={s['error_rate_pct']:.1f}%"
            )
            all_results.append(s)

        # 2. Dashboard
        print("\n>> Dashboard Analytics...")
        dash_results = await bench_dashboard(client, headers)
        for r in dash_results:
            s = r.summary()
            print(
                f"  {s['name']:30s} | {s['count']:4d} req | "
                f"p50={s['latency_ms']['p50']:7.1f}ms | p95={s['latency_ms']['p95']:7.1f}ms | "
                f"err={s['error_rate_pct']:.1f}%"
            )
            all_results.append(s)

        # 3. Ingestion
        print("\n>> Event Ingestion...")
        ing = await bench_sequential_ingestion(client, agent_headers, batch_size=50, count=20)
        s = ing.summary()
        print(
            f"  {s['name']:30s} | {s['count']:4d} req | "
            f"p50={s['latency_ms']['p50']:7.1f}ms | p95={s['latency_ms']['p95']:7.1f}ms | "
            f"thr={s['throughput_rps']:.1f} rps"
        )
        all_results.append(s)

        ing100 = await bench_sequential_ingestion(client, agent_headers, batch_size=100, count=10)
        s = ing100.summary()
        print(
            f"  {s['name']:30s} | {s['count']:4d} req | "
            f"p50={s['latency_ms']['p50']:7.1f}ms | p95={s['latency_ms']['p95']:7.1f}ms | "
            f"thr={s['throughput_rps']:.1f} rps"
        )
        all_results.append(s)

        # 4. Concurrent Ingestion
        if profile in ("normal", "heavy", "stress"):
            print("\n>> Concurrent Ingestion...")
            conc_ing = await bench_concurrent_ingestion(
                client, agent_headers, concurrency=10, batch_size=10
            )
            s = conc_ing.summary()
            print(
                f"  {s['name']:30s} | {s['count']:4d} req | "
                f"p50={s['latency_ms']['p50']:7.1f}ms | p95={s['latency_ms']['p95']:7.1f}ms | "
                f"thr={s['throughput_rps']:.1f} rps err={s['error_rate_pct']:.1f}%"
            )
            all_results.append(s)

        # 5. Concurrent Users
        print("\n>> Concurrent Users...")
        conc = await bench_concurrent_users(client, headers, concurrency=10)
        s = conc.summary()
        print(
            f"  {s['name']:30s} | {s['count']:4d} req | "
            f"p50={s['latency_ms']['p50']:7.1f}ms | p95={s['latency_ms']['p95']:7.1f}ms | "
            f"err={s['error_rate_pct']:.1f}%"
        )
        all_results.append(s)

        if profile in ("heavy", "stress"):
            conc50 = await bench_concurrent_users(client, headers, concurrency=50)
            s = conc50.summary()
            print(
                f"  {s['name']:30s} | {s['count']:4d} req | "
                f"p50={s['latency_ms']['p50']:7.1f}ms | p95={s['latency_ms']['p95']:7.1f}ms | "
                f"err={s['error_rate_pct']:.1f}%"
            )
            all_results.append(s)

        # 6. Search
        print("\n>> Search...")
        search_results = await bench_search(client, headers)
        for r in search_results:
            s = r.summary()
            print(
                f"  {s['name']:30s} | {s['count']:4d} req | "
                f"p50={s['latency_ms']['p50']:7.1f}ms | p95={s['latency_ms']['p95']:7.1f}ms | "
                f"err={s['error_rate_pct']:.1f}%"
            )
            all_results.append(s)

        # 7. Alert Mutations
        print("\n>> Alert Mutations...")
        mutations = await bench_alert_mutations(client, headers)
        s = mutations.summary()
        if s["count"] > 0:
            print(
                f"  {s['name']:30s} | {s['count']:4d} req | "
                f"p50={s['latency_ms']['p50']:7.1f}ms | p95={s['latency_ms']['p95']:7.1f}ms"
            )
            all_results.append(s)
        else:
            print("  (no alerts to mutate)")

        # 8. Reports
        print("\n>> Report Generation...")
        reports = await bench_report_generation(client, headers)
        s = reports.summary()
        print(
            f"  {s['name']:30s} | {s['count']:4d} req | "
            f"p50={s['latency_ms']['p50']:7.1f}ms | p95={s['latency_ms']['p95']:7.1f}ms"
        )
        all_results.append(s)

        # 9. Backpressure
        if profile in ("normal", "heavy", "stress"):
            print("\n>> Backpressure Test...")
            bp = await bench_backpressure(client, agent_headers)
            s = bp.summary()
            print(
                f"  {s['name']:30s} | {s['count']:4d} req | "
                f"p50={s['latency_ms']['p50']:7.1f}ms | p95={s['latency_ms']['p95']:7.1f}ms | "
                f"err={s['error_rate_pct']:.1f}%"
            )
            all_results.append(s)

        print(f"\n{'='*70}")
        print(f"  DONE — {len(all_results)} benchmarks completed")
        print(f"{'='*70}")

        return all_results


def main():
    parser = argparse.ArgumentParser(description="Securi_Sphere Performance Tests")
    parser.add_argument(
        "--profile",
        choices=["light", "normal", "heavy", "stress"],
        default="light",
        help="Test profile (default: light)",
    )
    parser.add_argument("--json", action="store_true", help="Output JSON results")
    args = parser.parse_args()

    results = asyncio.run(run_profile(args.profile))

    if args.json and results:
        print(json.dumps(results, indent=2))

    return results


if __name__ == "__main__":
    main()
