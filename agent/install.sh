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

if [[ -z "$TOKEN" || -z "$SERVER" ]]; then
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
if [[ ! -d "${INSTALL_DIR}/venv" ]]; then
  python3 -m venv "${INSTALL_DIR}/venv"
fi
"${INSTALL_DIR}/venv/bin/pip" install -q --upgrade pip
if ! "${INSTALL_DIR}/venv/bin/pip" install -q -r "${INSTALL_DIR}/requirements.txt"; then
  echo "[!] Failed to install Python dependencies from requirements.txt"
  exit 1
fi

if config_has_api_key; then
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
else
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
