# Member 3 — Linux Agent & Telemetry

> Linux agent, system monitoring, log collection, CPU/memory/disk metrics, process/network telemetry, heartbeat, SQLite offline buffer, retry/reconnect behavior, secure communication with backend.

---

## 1. What This Module Does

Member 3 owns the **Linux agent** — a lightweight Python daemon that runs on monitored hosts and collects security telemetry:

- **Log collection** — system logs (syslog, journald), authentication logs (auth.log/secure)
- **Metrics collection** — CPU usage, memory usage, disk usage, load average
- **Process telemetry** — running processes, command lines
- **Network telemetry** — active connections, listening ports
- **Heartbeat** — periodic alive signals to backend (30s interval)
- **Offline buffering** — SQLite local buffer when network is unavailable
- **Retry/reconnect** — exponential backoff on connection failures, auto-flush on reconnect
- **Secure communication** — HMAC-SHA256 signed requests with nonce + timestamp validation
- **Agent integrity** — file integrity checking for agent binaries
- **Installation** — one-line install script with systemd service

---

## 2. Main Files & Folders

### Agent Core (`agent/agent/`)

| File | Purpose |
|------|---------|
| `agent/__init__.py` | Package init |
| `agent/main.py` | Agent entry point — main loop, signal handling, scheduler |
| `agent/config.py` | Configuration management (YAML/env vars) |
| `agent/buffer.py` | SQLite offline buffer for events when network is down |
| `agent/sender.py` | HTTP sender with HMAC-SHA256 signing, retry logic |
| `agent/integrity.py` | Agent binary integrity checking |

### Collectors (`agent/agent/collector/`)

| File | Purpose |
|------|---------|
| `collector/__init__.py` | Collector package |
| `collector/logs.py` | System log collection (syslog, journald, auth.log) |
| `collector/metrics.py` | CPU, memory, disk, load average metrics |
| `collector/events.py` | Security event collection (login, process, network) |

### Installation & Deployment

| File | Purpose |
|------|---------|
| `agent/install.sh` | One-line installer (downloads, configures, enables systemd) |
| `agent/securi-agent.service` | systemd service unit file |
| `agent/requirements.txt` | Python dependencies |
| `agent/.agent-bundle.tar.gz` | Pre-built agent bundle |
| `agent/agent-bundle.tar.gz` | Agent bundle for distribution |

### Tests (`agent/tests/`)

| File | Purpose |
|------|---------|
| `tests/__init__.py` | Test package |
| `tests/conftest.py` | Pytest fixtures |
| `tests/test_main.py` | Main loop tests |
| `tests/test_config.py` | Configuration tests |
| `tests/test_buffer.py` | SQLite buffer tests |
| `tests/test_sender.py` | HMAC sender tests |
| `tests/test_integrity.py` | Integrity check tests |
| `tests/test_collector_events.py` | Event collector tests |
| `tests/test_collector_metrics.py` | Metrics collector tests |

---

## 3. Architecture / Design

### Agent Lifecycle

```
install.sh → securi-agent.service → main.py
                                       │
                    ┌────────────────────┤
                    │                    │
              ┌─────▼─────┐      ┌──────▼──────┐
              │  Collector  │      │   Sender     │
              │  (10-30s)   │      │  (HMAC-signed)│
              └─────┬──────┘      └──────┬───────┘
                    │                    │
              ┌─────▼──────┐      ┌──────▼───────┐
              │  SQLite     │      │  Backend      │
              │  Buffer     │      │  (HTTP/JSON)  │
              │  (offline)  │      │               │
              └────────────┘      └──────────────┘
```

### Collection Intervals

| Data Type | Interval | Description |
|-----------|----------|-------------|
| Heartbeat | 30s | Alive signal with host status |
| Metrics | 30s | CPU, memory, disk, load average |
| Logs | 10s | System and auth log tail |
| Events | On-change | Process starts, network connections |

### Offline Buffer Flow

```
1. Event occurs → Collector captures it
2. Network available? → YES: Sender sends immediately
                     → NO:  Buffer stores in SQLite
3. Network reconnects → Buffer flushes all pending events
4. Retry on failure → Exponential backoff (1s, 2s, 4s, 8s, max 30s)
```

### HMAC-SHA256 Signing

Every request to the backend is signed:

```
Request:
  - Timestamp (Unix epoch)
  - Nonce (random, single-use)
  - Payload (JSON body)

Signature:
  HMAC-SHA256(secret_key, timestamp + nonce + payload)

Headers:
  X-Agent-Timestamp: <timestamp>
  X-Agent-Nonce: <nonce>
  X-Agent-Signature: <hmac_signature>
```

Backend validates:
1. Timestamp within ±5 minutes (prevents replay)
2. Nonce not seen before (single-use)
3. Signature matches computed HMAC

---

## 4. Important Implementation Details

- **SQLite buffer** uses WAL mode for concurrent reads during writes
- **Graceful shutdown** on SIGTERM/SIGINT — flushes buffer before exit
- **Systemd integration** — auto-restart on failure, resource limits
- **Config via YAML** or environment variables (env vars take precedence)
- **Python 3.11+** required — uses modern async features
- **No external dependencies** beyond `requests` and `psutil` for lightweight footprint
- **Integrity checking** verifies agent binary hashes on startup

---

## 5. Technologies Used

| Technology | Purpose |
|-----------|---------|
| Python 3.11+ | Agent runtime |
| requests | HTTP client for backend communication |
| psutil | System metrics (CPU, memory, disk, network) |
| SQLite3 | Offline event buffer (built-in, no extra deps) |
| hashlib | HMAC-SHA256 request signing |
| PyYAML | Configuration file parsing |
| systemd | Service management on Linux |
| pytest | Testing framework |

---

## 6. Testing

### Running Tests

```bash
cd agent

# All tests
pytest tests/ -v

# Specific test file
pytest tests/test_buffer.py -v

# With coverage
pytest tests/ -v --cov=agent --cov-report=term-missing
```

### Test Coverage Areas

- **Buffer:** SQLite write/read, flush, overflow, concurrent access
- **Sender:** HMAC signing, retry logic, timeout handling
- **Config:** YAML parsing, env var overrides, defaults
- **Collectors:** Log parsing, metric collection, event detection
- **Integrity:** Hash verification, tamper detection
- **Main:** Signal handling, lifecycle, error recovery

### Test Count: 67 tests

---

## 7. Screenshots / Diagrams for Report

Include these in the final report:

| Screenshot/Diagram | Description |
|-------------------|-------------|
| Agent installation | One-line install script output |
| systemd status | `systemctl status securi-agent` showing running state |
| SQLite buffer | Database file with buffered events |
| Agent → Backend flow | HMAC-signed request/response sequence |
| Offline→Online transition | Buffer flush after network reconnect |
| Host dashboard | Backend showing agent-connected host with metrics |

---

## 8. Possible Viva Questions

### Architecture
1. **Q: Why Python for the agent instead of a compiled language?**
   A: Rapid development, rich ecosystem (psutil), cross-platform potential. The agent is lightweight enough — Python's overhead is negligible for 30s collection intervals.

2. **Q: How does the offline buffer work?**
   A: SQLite with WAL mode stores events when network is unavailable. On reconnect, events are flushed in FIFO order with retry logic. No data loss even during extended outages.

### Security
3. **Q: How do you prevent replay attacks on agent communication?**
   A: Three mechanisms: timestamp validation (±5 min window), single-use nonces, HMAC-SHA256 signature. Backend rejects any request failing any check.

4. **Q: What happens if the agent binary is tampered with?**
   A: Integrity checking verifies SHA-256 hashes of agent files on startup. Mismatch triggers alert and optional self-shutdown.

### Reliability
5. **Q: How does the agent handle network failures?**
   A: Exponential backoff (1s → 30s max). Events buffered locally. Auto-flush on reconnect. No data loss.

6. **Q: How does the agent handle backend restarts?**
   A: Agent detects connection failure, switches to buffer mode, continues collecting. On backend recovery, flushes buffer and resumes normal operation.

### Performance
7. **Q: What is the agent's resource footprint?**
   A: ~10MB RAM, negligible CPU (30s intervals). SQLite buffer is append-only with periodic cleanup. No heavy dependencies.
