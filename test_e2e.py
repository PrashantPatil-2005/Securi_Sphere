import sys, os
sys.path.insert(0, r'C:\Users\Prash\Desktop\Securi\backend')
sys.path.insert(0, r'C:\Users\Prash\Desktop\Securi\agent')

from agent.collector.events import parse_line

print('=== Test 1: Agent sends typed events ===')
attack_lines = [
    # 12 failed logins (brute force)
    ('Failed password for admin from 192.168.1.50 port 52752 ssh2', 'auth.log'),
    ('Failed password for admin from 192.168.1.50 port 52753 ssh2', 'auth.log'),
    ('Failed password for admin from 192.168.1.50 port 52754 ssh2', 'auth.log'),
    ('Failed password for admin from 192.168.1.50 port 52755 ssh2', 'auth.log'),
    ('Failed password for admin from 192.168.1.50 port 52756 ssh2', 'auth.log'),
    ('Failed password for admin from 192.168.1.50 port 52757 ssh2', 'auth.log'),
    ('Failed password for admin from 192.168.1.50 port 52758 ssh2', 'auth.log'),
    ('Failed password for admin from 192.168.1.50 port 52759 ssh2', 'auth.log'),
    ('Failed password for admin from 192.168.1.50 port 52760 ssh2', 'auth.log'),
    ('Failed password for admin from 192.168.1.50 port 52761 ssh2', 'auth.log'),
    ('Failed password for admin from 192.168.1.50 port 52762 ssh2', 'auth.log'),
    ('Failed password for admin from 192.168.1.50 port 52763 ssh2', 'auth.log'),
    # Successful login
    ('Accepted password for admin from 192.168.1.50 port 52764 ssh2', 'auth.log'),
    # Privilege escalation
    ('session opened for user admin', 'auth.log'),
]

typed_events = []
for line, source in attack_lines:
    result = parse_line(line, source)
    if result:
        typed_events.append(result)
        ip = result.get('source_ip', 'N/A')
        user = result.get('username', 'N/A')
        etype = result['event_type']
        desc = result['description']
        print(f'  {etype}: {desc} (ip={ip}, user={user})')
    else:
        print(f'  FAIL: {line[:50]}')

print()
print(f'Total typed events: {len(typed_events)}')
event_types = set(e['event_type'] for e in typed_events)
print(f'Event types present: {event_types}')

# Test 2: Kill chain verification
print('\n=== Test 2: Kill chain verification ===')
has_failure = 'ssh_login_failure' in event_types
has_success = 'ssh_login_success' in event_types or 'root_login' in event_types
has_sudo = 'sudo_usage' in event_types

print(f'  Has ssh_login_failure: {has_failure}')
print(f'  Has ssh_login_success/root_login: {has_success}')
print(f'  Has sudo_usage: {has_sudo}')

if has_failure and has_success and has_sudo:
    print('  PASS: Full kill chain events present')
else:
    print('  FAIL: Missing events for full kill chain')

# Test 3: Check that events have source_ip and username
print('\n=== Test 3: Events have enriched data ===')
for e in typed_events:
    has_ip = e.get('source_ip') is not None
    has_user = e.get('username') is not None
    etype = e['event_type']
    print(f'  {etype}: ip={has_ip}, user={has_user}')