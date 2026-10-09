#!/usr/bin/env python
import urllib.request
import os
import sys
import tarfile
import json
import re

token = "enroll_U0unDDUT_xM7DkBvHaNTT4pdQjAhG2vu5bg-TkvfFwQ"
server = "http://10.0.9.93:8000"

# Step 1: Download the agent bundle
bundle_url = f"{server}/agent-bundle.tar.gz"
print(f"Downloading agent bundle from {bundle_url}...")

try:
    r = urllib.request.urlopen(bundle_url, timeout=30)
    bundle_data = r.read()
    print(f"Downloaded {len(bundle_data)} bytes")
    
    # Save the bundle
    bundle_path = "/tmp/agent-bundle.tar.gz"
    with open(bundle_path, "wb") as f:
        f.write(bundle_data)
    print(f"Saved to {bundle_path}")
    
except Exception as e:
    print(f"Failed to download bundle: {e}")
    sys.exit(1)

# Step 2: Extract and install
print("Extracting agent bundle...")
try:
    extract_dir = "/opt/securi-agent"
    os.makedirs(extract_dir, exist_ok=True)
    
    with tarfile.open(bundle_path, "r:gz") as tar:
        tar.extractall(path=extract_dir)
    print(f"Extracted to {extract_dir}")
    
    # Check if main.py exists
    main_py = os.path.join(extract_dir, "agent", "main.py")
    if os.path.exists(main_py):
        print(f"Agent main.py found at {main_py}")
    else:
        print(f"Agent main.py not found at expected path")
        # List what we have
        agent_dir = os.path.join(extract_dir, "agent")
        if os.path.exists(agent_dir):
            print(f"Agent directory contents: {os.listdir(agent_dir)}")
            
except Exception as e:
    print(f"Failed to extract: {e}")
    sys.exit(1)

# Step 3: Setup Python environment
print("Setting up Python environment...")
try:
    import venv
    venv_path = os.path.join(extract_dir, "venv")
    if not os.path.exists(venv_path):
        venv.create(extract_dir, with_pip=True)
        print(f"Created venv at {venv_path}")
    else:
        print(f"Venv already exists at {venv_path}")
    
    venv_python = os.path.join(venv_path, "bin", "python")
    
    # Install dependencies
    print("Installing dependencies...")
    req_path = os.path.join(extract_dir, "requirements.txt")
    if os.path.exists(req_path):
        ret = os.system(f'"{venv_python}" -m pip install -q -r "{req_path}"')
        if ret != 0:
            print("pip install failed, trying with --upgrade")
            ret = os.system(f'"{venv_python}" -m pip install -q --upgrade -r "{req_path}"')
    
    # Import check
    print("Verifying dependencies...")
    ret = os.system(f'"{venv_python}" -c "import psutil, requests"')
    if ret == 0:
        print("Dependencies verified!")
    else:
        print("Dependencies could not be imported")
        
except Exception as e:
    print(f"Environment setup error: {e}")
    sys.exit(1)

# Step 4: Register the agent
print("Registering agent...")
try:
    import requests
    register_url = f"{server}/api/v1/agent/register"
    hostname = os.popen("hostname").read().strip()
    ip_result = os.popen("hostname -I").read().strip()
    ip_address = ip_result.split()[0] if ip_result else None
    os_info_result = os.popen("uname -s && uname -r").read().strip()
    os_info = os_info_result.replace("\n", " ")
    
    payload = {
        "enrollment_token": token,
        "hostname": hostname,
        "ip_address": ip_address,
        "os_info": os_info
    }
    print(f"Registering with payload (hostname={hostname}, ip={ip_address})")
    
    r = requests.post(register_url, json=payload, timeout=30)
    print(f"Registration response: {r.status_code}")
    
    if r.status_code == 200:
        api_key = r.json().get("api_key")
        print(f"API Key: {api_key}")
        
        # Save config
        config = {
            "server_url": server,
            "api_key": api_key,
            "signing_enabled": False
        }
        config_path = "/etc/securi/config.json"
        os.makedirs("/etc/securi", exist_ok=True)
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        os.chmod(config_path, 0o600)
        print(f"Configuration saved to {config_path}")
    else:
        print(f"Registration failed: {r.text}")
        
except Exception as e:
    print(f"Registration error: {e}")
    sys.exit(1)

# Step 5: Setup systemd service
print("Setting up systemd service...")
try:
    service_content = f"""[Unit]
Description=Securi Security Monitoring Agent
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart={extract_dir}/venv/bin/python3 -m agent.main
WorkingDirectory={extract_dir}
Restart=always
RestartSec=10
User=root

[Install]
WantedBy=multi-user.target
"""
    with open("/etc/systemd/system/securi-agent.service", "w") as f:
        f.write(service_content)
    print("Service file created")
    
    # Enable and start
    ret1 = os.system("systemctl daemon-reload 2>/dev/null")
    ret2 = os.system("systemctl enable securi-agent 2>/dev/null")
    ret3 = os.system("systemctl start securi-agent 2>/dev/null")
    ret4 = os.system("systemctl status securi-agent --no-pager 2>/dev/null")
    print(f"daemon-reload: {ret1}, enable: {ret2}, start: {ret3}, status: {ret4}")
    
except Exception as e:
    print(f"Service setup error: {e}")

print("\n=== Agent Installation Complete ===")