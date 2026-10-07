import sys
sys.path.insert(0, r'C:\Users\Prash\Desktop\Securi\backend')
sys.path.insert(0, r'C:\Users\Prash\Desktop\Securi\agent')
from agent.collector.events import parse_line

# Test various real auth.log patterns
tests = [
    # Standard failure
    ('Failed password for admin from 192.168.1.100 port 52752 ssh2', 'auth.log'),
    # Invalid user
    ('Invalid user attacker from 10.0.0.1 port 49152 ssh2', 'auth.log'),
    # Success
    ('Accepted password for admin from 192.168.1.100 port 52752 ssh2', 'auth.log'),
    # Root success
    ('Accepted publickey for root from 192.168.1.100 port 52752 ssh2', 'auth.log'),
    # Sudo
    ('sudo: pam_unix(sudo: session opened for admin by admin)', 'auth.log'),
    # Service stop
    ('Stopped sshd', 'syslog'),
    # Service start
    ('Started sshd', 'syslog'),
    # Service failure
    ('Failed to start nginx', 'syslog'),
    # GSSAPI failure
    ('Failed gssapi-with-mic for user from 192.168.1.100 port 52752 ssh2', 'auth.log'),
    # Keyboard-interactive
    ('Failed keyboard-interactive for admin from 10.0.0.1 port 49152 ssh2', 'auth.log'),
]

for line, source in tests:
    result = parse_line(line, source)
    if result:
        etype = result["event_type"]
        desc = result["description"]
        ip = result.get("source_ip", "N/A")
        user = result.get("username", "N/A")
        print(f'OK -> {etype}: {desc} (ip={ip}, user={user})')
    else:
        print(f'FAIL -> no match: {line[:60]}')