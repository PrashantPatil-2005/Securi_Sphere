#!/bin/bash
set -euo pipefail

TOKEN=""
SERVER=""

while [[ $# -gt 0 ]]; do
  case $1 in
    --token) TOKEN="$2"; shift 2 ;;
    --server) SERVER="$2"; shift 2 ;;
    *) echo "[!] Unknown option: $1"; exit 1 ;;
  esac
done

if [[ -z "$SERVER" ]]; then
  echo "Usage: install.sh --token TOKEN --server SERVER_URL"
  echo "  Local:  sudo ./install.sh --token TOKEN --server http://HOST:8000"
  echo "  Remote: curl -fsSL http://HOST:8000/install.sh | sudo bash -s -- --token TOKEN --server http://HOST:8000"
  exit 1
fi

if [[ $EUID -ne 0 ]]; then
  echo "[!] Run as root: sudo ./install.sh --token ... --server ..."
  exit 1
fi

if ! command -v apt-get >/dev/null 2>&1; then
  echo "[!] apt-get not found. This installer supports Debian, Ubuntu, and Kali Linux."
  exit 1
fi

# Strip trailing slash from server URL
SERVER="${SERVER%/}"

INSTALL_DIR="/opt/securi-agent"
CONFIG_FILE="/etc/securi/config.json"
SERVICE_NAME="securi-agent"

# Resolve script directory only when executed from a real file (not curl | bash).
# ${var:-} avoids 'unbound variable' under set -u when BASH_SOURCE is unset.
resolve_script_dir() {
  local candidate=""

  if [[ -n "${BASH_SOURCE[0]:-}" ]]; then
    candidate="${BASH_SOURCE[0]}"
    if [[ "$candidate" == bash || "$candidate" == /bin/bash || "$candidate" == /usr/bin/bash ]]; then
      candidate=""
    elif [[ ! -f "$candidate" ]]; then
      candidate=""
    fi
  fi

  if [[ -z "$candidate" && -n "${0:-}" ]]; then
    candidate="$0"
    if [[ "$candidate" == bash || "$candidate" == -bash || "$candidate" == /bin/bash || "$candidate" == /usr/bin/bash ]]; then
      candidate=""
    elif [[ ! -f "$candidate" ]]; then
      candidate=""
    fi
  fi

  if [[ -n "$candidate" ]]; then
    (cd "$(dirname "$candidate")" && pwd)
  fi
}

install_agent_files_from_local() {
  local script_dir="$1"
  echo "[*] Installing agent files from local bundle (${script_dir})..."
  rm -rf "${INSTALL_DIR}/agent"
  cp -a "${script_dir}/agent" "${INSTALL_DIR}/agent"
  cp -a "${script_dir}/requirements.txt" "${INSTALL_DIR}/requirements.txt"
}

bundle_contains_agent_main() {
  local archive="$1"
  tar -tzf "$archive" | sed 's|^\./||' | tr '\\' '/' | grep -qx 'agent/main.py'
}

install_agent_files_from_remote() {
  local bundle_url="${SERVER}/agent-bundle.tar.gz"
  local tmp_bundle
  tmp_bundle="$(mktemp /tmp/securi-agent-bundle.XXXXXX.tar.gz)"

  echo "[*] Downloading agent bundle from ${bundle_url}..."
  if ! curl -fsSL "$bundle_url" -o "$tmp_bundle"; then
    rm -f "$tmp_bundle"
    echo "[!] Failed to download agent bundle from ${bundle_url}"
    echo "[!] Check that the server is reachable and /agent-bundle.tar.gz is served."
    exit 1
  fi

  if [[ ! -s "$tmp_bundle" ]]; then
    rm -f "$tmp_bundle"
    echo "[!] Downloaded agent bundle is empty."
    exit 1
  fi

  if ! tar -tzf "$tmp_bundle" >/dev/null 2>&1; then
    rm -f "$tmp_bundle"
    echo "[!] Downloaded file is not a valid gzip tarball."
    exit 1
  fi

  if ! bundle_contains_agent_main "$tmp_bundle"; then
    echo "[!] Bundle does not contain agent/main.py"
    echo "[!] Archive listing:"
    tar -tzf "$tmp_bundle" 2>/dev/null | sed 's/^/    /' || true
    echo "[!] Rebuild on the server: python scripts/build_agent_bundle.py"
    rm -f "$tmp_bundle"
    exit 1
  fi

  rm -rf "${INSTALL_DIR}/agent" "${INSTALL_DIR}/requirements.txt"
  if ! tar -xzf "$tmp_bundle" -C "$INSTALL_DIR"; then
    rm -f "$tmp_bundle"
    echo "[!] Failed to extract agent bundle into ${INSTALL_DIR}"
    exit 1
  fi

  rm -f "$tmp_bundle"
}

register_agent() {
  local hostname ip os_info api_key

  hostname="$(hostname)"
  ip="$(hostname -I 2>/dev/null | awk '{print $1}')"
  os_info="$(python3 -c "import platform; print(platform.system(), platform.release())")"

  echo "[*] Registering agent with ${SERVER}..."
  if ! api_key="$(
    "${INSTALL_DIR}/venv/bin/python3" <<PY
import requests
import sys

server = "${SERVER}"
token = "${TOKEN}"
payload = {
    "enrollment_token": token,
    "hostname": "${hostname}",
    "ip_address": "${ip}" or None,
    "os_info": "${os_info}",
}
try:
    r = requests.post(f"{server}/api/v1/agent/register", json=payload, timeout=30)
    r.raise_for_status()
    print(r.json()["api_key"])
except requests.HTTPError as e:
    print(f"Registration failed: HTTP {e.response.status_code}", file=sys.stderr)
    if e.response is not None:
        print(e.response.text, file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"Registration failed: {e}", file=sys.stderr)
    sys.exit(1)
PY
  )"; then
    echo "[!] Agent registration failed."
    exit 1
  fi

  if [[ -z "$api_key" ]]; then
    echo "[!] Registration returned an empty API key."
    exit 1
  fi

  cat > "$CONFIG_FILE" <<EOF
{
  "server_url": "${SERVER}",
  "api_key": "${api_key}",
  "signing_enabled": false
}
EOF
  chmod 600 "$CONFIG_FILE"
  echo "[*] Agent registered and configuration saved to ${CONFIG_FILE}"
}

config_has_api_key() {
  [[ -f "$CONFIG_FILE" ]] || return 1
  "${INSTALL_DIR}/venv/bin/python3" - <<'PY' 2>/dev/null
import json, sys
from pathlib import Path
cfg = json.loads(Path("/etc/securi/config.json").read_text())
sys.exit(0 if cfg.get("api_key") else 1)
PY
}

validate_existing_credentials() {
  # Returns 0 if existing credentials are accepted by the server, 1 otherwise.
  # Uses the heartbeat endpoint — lightweight, no state mutation.
  "${INSTALL_DIR}/venv/bin/python3" - <<PY 2>/dev/null
import json, sys
from pathlib import Path
import requests

cfg = json.loads(Path("${CONFIG_FILE}").read_text())
server = cfg.get("server_url", "")
api_key = cfg.get("api_key", "")
if not server or not api_key:
    sys.exit(1)
try:
    r = requests.post(
        f"{server.rstrip('/')}/api/v1/agent/heartbeat",
        headers={"X-API-Key": api_key},
        timeout=10,
    )
    sys.exit(0 if r.status_code == 200 else 1)
except requests.RequestException:
    sys.exit(1)
PY
}

echo "[*] Installing Securi Agent..."
echo "[*] Server: ${SERVER}"

echo "[*] Installing system packages..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv curl ca-certificates tar

mkdir -p "$INSTALL_DIR" /etc/securi /var/lib/securi

SCRIPT_DIR="$(resolve_script_dir || true)"
if [[ -n "$SCRIPT_DIR" && -d "${SCRIPT_DIR}/agent" && -f "${SCRIPT_DIR}/requirements.txt" ]]; then
  install_agent_files_from_local "$SCRIPT_DIR"
else
  if [[ -n "$SCRIPT_DIR" ]]; then
    echo "[*] Local agent/ directory not found beside install.sh; downloading bundle from server."
  else
    echo "[*] Running from remote pipe (curl | bash); downloading bundle from server."
  fi
  install_agent_files_from_remote
fi

if [[ ! -f "${INSTALL_DIR}/agent/main.py" ]]; then
  echo "[!] Agent files missing after install. Expected ${INSTALL_DIR}/agent/main.py"
  exit 1
fi

if [[ ! -f "${INSTALL_DIR}/requirements.txt" ]]; then
  echo "[!] requirements.txt missing after install. Expected ${INSTALL_DIR}/requirements.txt"
  exit 1
fi

echo "[*] Setting up Python virtual environment..."

# Detect system Python version (e.g. "3.14")
SYS_PY_VERSION="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
echo "[*] System Python: ${SYS_PY_VERSION}"

VENV_CREATED_VERSION=""
if [[ -f "${INSTALL_DIR}/venv/pyvenv.cfg" ]]; then
  VENV_CREATED_VERSION="$(grep -oP 'version\s*=\s*\K[0-9]+\.[0-9]+' "${INSTALL_DIR}/venv/pyvenv.cfg" 2>/dev/null || true)"
fi

# Recreate venv if missing or if it was created with a different Python version
if [[ ! -d "${INSTALL_DIR}/venv" || -z "$VENV_CREATED_VERSION" || "$VENV_CREATED_VERSION" != "$SYS_PY_VERSION" ]]; then
  if [[ -d "${INSTALL_DIR}/venv" ]]; then
    echo "[*] Existing venv was created with Python ${VENV_CREATED_VERSION:-unknown}, system has ${SYS_PY_VERSION}. Recreating..."
  else
    echo "[*] No existing venv found."
  fi
  rm -rf "${INSTALL_DIR}/venv"
  python3 -m venv "${INSTALL_DIR}/venv"
  echo "[*] Created venv with Python ${SYS_PY_VERSION}"
fi

VENV_PY="${INSTALL_DIR}/venv/bin/python"

# Ensure pip is available in the venv
if ! "$VENV_PY" -m pip --version >/dev/null 2>&1; then
  echo "[*] pip not available in venv, bootstrapping..."

  # Method 1: ensurepip (works when python3-venv includes the pip wheel)
  "$VENV_PY" -m ensurepip --upgrade 2>/dev/null && echo "[*] Bootstrapped pip via ensurepip." || true

  # Method 2: install python3-pip via apt, then ensurepip picks it up
  if ! "$VENV_PY" -m pip --version >/dev/null 2>&1; then
    echo "[*] ensurepip did not provide pip, trying apt..."
    apt-get install -y -qq python3-pip >/dev/null 2>&1 || true
    "$VENV_PY" -m ensurepip --upgrade 2>/dev/null && echo "[*] Bootstrapped pip via apt + ensurepip." || true
  fi

  # Method 3: get-pip.py (last resort when system packages lack pip for this Python)
  if ! "$VENV_PY" -m pip --version >/dev/null 2>&1; then
    echo "[*] Falling back to get-pip.py..."
    GET_PIP_TMP="$(mktemp /tmp/get-pip.XXXXXX.py)"
    if curl -fsSL "https://bootstrap.pypa.io/get-pip.py" -o "$GET_PIP_TMP" 2>/dev/null; then
      "$VENV_PY" "$GET_PIP_TMP" 2>/dev/null && echo "[*] Bootstrapped pip via get-pip.py." || echo "[!] get-pip.py failed."
    else
      echo "[!] Could not download get-pip.py."
    fi
    rm -f "$GET_PIP_TMP"
  fi
fi

# Final pip check — fail hard if pip is not available
if ! "$VENV_PY" -m pip --version >/dev/null 2>&1; then
  echo "[!] FATAL: Cannot obtain a working pip for Python ${SYS_PY_VERSION}."
  echo "[!] Install python3-pip manually and retry."
  exit 1
fi
echo "[*] pip: $($VENV_PY -m pip --version 2>&1)"

# Install dependencies (never upgrade pip itself — the bundled version is tested with this Python)
if ! "$VENV_PY" -m pip install -q -r "${INSTALL_DIR}/requirements.txt"; then
  echo "[!] Failed to install Python dependencies from requirements.txt"
  exit 1
fi

# Verify that every third-party import the agent needs actually resolved
echo "[*] Verifying agent dependencies..."
if ! "$VENV_PY" -c "import psutil, requests" 2>/dev/null; then
  echo "[!] Dependency check failed — retrying with --force-reinstall..."
  "$VENV_PY" -m pip install --force-reinstall -q -r "${INSTALL_DIR}/requirements.txt"
  if ! "$VENV_PY" -c "import psutil, requests" 2>/dev/null; then
    echo "[!] FATAL: Agent dependencies (psutil, requests) could not be installed."
    echo "[!] Check network connectivity and that Python ${SYS_PY_VERSION} has compatible wheels."
    exit 1
  fi
fi
echo "[*] Agent dependencies verified."

if config_has_api_key; then
  if [[ -n "$TOKEN" ]]; then
    # Token explicitly provided — validate existing credentials first.
    if validate_existing_credentials; then
      echo "[*] Existing credentials are valid — preserving them."
      # Update server URL in case it changed, keep api_key
      "${INSTALL_DIR}/venv/bin/python3" - <<PY
import json
from pathlib import Path
p = Path("${CONFIG_FILE}")
cfg = json.loads(p.read_text())
cfg["server_url"] = "${SERVER}"
p.write_text(json.dumps(cfg, indent=2) + "\n")
p.chmod(0o600)
PY
    else
      echo "[*] Existing credentials are invalid — re-registering with provided token."
      register_agent
    fi
  else
    echo "[*] Existing configuration found — skipping registration (idempotent reinstall)."
    # Update server URL in case it changed, keep api_key
    "${INSTALL_DIR}/venv/bin/python3" - <<PY
import json
from pathlib import Path
p = Path("${CONFIG_FILE}")
cfg = json.loads(p.read_text())
cfg["server_url"] = "${SERVER}"
p.write_text(json.dumps(cfg, indent=2) + "\n")
p.chmod(0o600)
PY
  fi
else
  if [[ -z "$TOKEN" ]]; then
    echo "[!] No existing configuration and no enrollment token provided."
    echo "[!] Usage: install.sh --token TOKEN --server SERVER_URL"
    exit 1
  fi
  register_agent
fi

echo "[*] Installing systemd service..."
cat > "/etc/systemd/system/${SERVICE_NAME}.service" <<EOF
[Unit]
Description=Securi Security Monitoring Agent
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=${INSTALL_DIR}/venv/bin/python3 -m agent.main
WorkingDirectory=${INSTALL_DIR}
Restart=always
RestartSec=10
User=root
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "${SERVICE_NAME}"

if systemctl is-active --quiet "${SERVICE_NAME}" 2>/dev/null; then
  systemctl restart "${SERVICE_NAME}"
else
  systemctl start "${SERVICE_NAME}"
fi

sleep 2
if systemctl is-active --quiet "${SERVICE_NAME}"; then
  echo "[+] Securi agent installed and running."
else
  echo "[!] Agent failed to start. Check logs:"
  echo "    journalctl -u ${SERVICE_NAME} -n 50 --no-pager"
  exit 1
fi

systemctl status "${SERVICE_NAME}" --no-pager
