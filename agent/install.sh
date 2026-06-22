#!/bin/bash
set -euo pipefail

TOKEN=""
SERVER=""

while [[ $# -gt 0 ]]; do
  case $1 in
    --token) TOKEN="$2"; shift 2 ;;
    --server) SERVER="$2"; shift 2 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

if [[ -z "$TOKEN" || -z "$SERVER" ]]; then
  echo "Usage: install.sh --token TOKEN --server SERVER_URL"
  exit 1
fi

if [[ $EUID -ne 0 ]]; then
  echo "[!] Run as root: sudo bash install.sh --token ... --server ..."
  exit 1
fi

if ! command -v apt-get >/dev/null 2>&1; then
  echo "[!] Debian/Ubuntu required (apt-get not found)."
  exit 1
fi

echo "[*] Installing Securi Agent..."
echo "[*] Server: ${SERVER}"

apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv curl ca-certificates

INSTALL_DIR="/opt/securi-agent"
mkdir -p "$INSTALL_DIR"
mkdir -p /etc/securi
mkdir -p /var/lib/securi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -d "$SCRIPT_DIR/agent" ]]; then
  cp -r "$SCRIPT_DIR/agent" "$INSTALL_DIR/"
  cp "$SCRIPT_DIR/requirements.txt" "$INSTALL_DIR/"
else
  echo "[*] Downloading agent bundle from ${SERVER}..."
  if ! curl -fsSL "${SERVER}/agent-bundle.tar.gz" | tar -xz -C "$INSTALL_DIR"; then
    echo "[!] Failed to download agent bundle from ${SERVER}/agent-bundle.tar.gz"
    exit 1
  fi
fi

if [[ ! -f "$INSTALL_DIR/agent/main.py" ]]; then
  echo "[!] Agent files missing after install. Expected ${INSTALL_DIR}/agent/main.py"
  exit 1
fi

python3 -m venv "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/pip" install -q -r "$INSTALL_DIR/requirements.txt"

HOSTNAME=$(hostname)
IP=$(hostname -I 2>/dev/null | awk '{print $1}')
OS=$(python3 -c "import platform; print(platform.system(), platform.release())")

echo "[*] Registering agent with server..."
API_KEY=$("$INSTALL_DIR/venv/bin/python3" -c "
import requests, sys
try:
    r = requests.post('${SERVER}/api/v1/agent/register', json={
        'enrollment_token': '${TOKEN}',
        'hostname': '${HOSTNAME}',
        'ip_address': '${IP}',
        'os_info': '${OS}',
    }, timeout=30)
    r.raise_for_status()
    print(r.json()['api_key'])
except Exception as e:
    print(f'Registration failed: {e}', file=sys.stderr)
    if hasattr(e, 'response') and e.response is not None:
        print(e.response.text, file=sys.stderr)
    sys.exit(1)
")

cat > /etc/securi/config.json <<EOF
{
  "server_url": "${SERVER}",
  "api_key": "${API_KEY}",
  "signing_enabled": false
}
EOF
chmod 600 /etc/securi/config.json

cat > /etc/systemd/system/securi-agent.service <<EOF
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
systemctl enable securi-agent
systemctl restart securi-agent

sleep 2
if systemctl is-active --quiet securi-agent; then
  echo "[+] Securi agent installed and running."
else
  echo "[!] Agent failed to start. Check: journalctl -u securi-agent -n 50"
  exit 1
fi
systemctl status securi-agent --no-pager
