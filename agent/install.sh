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

echo "[*] Installing Securi Agent..."

apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv curl

INSTALL_DIR="/opt/securi-agent"
mkdir -p "$INSTALL_DIR"
mkdir -p /etc/securi
mkdir -p /var/lib/securi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -d "$SCRIPT_DIR/agent" ]]; then
  cp -r "$SCRIPT_DIR/agent" "$INSTALL_DIR/"
  cp "$SCRIPT_DIR/requirements.txt" "$INSTALL_DIR/"
else
  curl -sSL "${SERVER}/agent-bundle.tar.gz" | tar -xz -C "$INSTALL_DIR" 2>/dev/null || {
    echo "[!] Agent files not found locally. Copy agent/ to $INSTALL_DIR manually."
  }
fi

python3 -m venv "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/pip" install -q -r "$INSTALL_DIR/requirements.txt"

HOSTNAME=$(hostname)
IP=$(hostname -I | awk '{print $1}')
OS=$(python3 -c "import platform; print(platform.system(), platform.release())")

API_KEY=$("$INSTALL_DIR/venv/bin/python3" -c "
import requests, sys
r = requests.post('${SERVER}/api/v1/agent/register', json={
    'enrollment_token': '${TOKEN}',
    'hostname': '${HOSTNAME}',
    'ip_address': '${IP}',
    'os_info': '${OS}',
}, timeout=30)
r.raise_for_status()
print(r.json()['api_key'])
")

cat > /etc/securi/config.json <<EOF
{
  "server_url": "${SERVER}",
  "api_key": "${API_KEY}"
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

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable securi-agent
systemctl restart securi-agent

echo "[+] Securi agent installed and started."
systemctl status securi-agent --no-pager
