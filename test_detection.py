import sys, os
sys.path.insert(0, r'C:\Users\Prash\Desktop\Securi\backend')
sys.path.insert(0, r'C:\Users\Prash\Desktop\Securi\agent')

from agent.collector.events import parse_line

print('=== Test 1: Agent sends typed events ===')
attack_lines = [
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
    ('Accepted password for admin from 192.168.1.50 port 52764 ssh2', 'auth.log'),
    ('session opened for user admin', 'auth.log'),
]

typed_events = []
for line, source in attack_lines:
    result = parse_line(line, source)
    if result:
        typed_events.append(result)
        ip = result.get('source_ip', 'N/A') or 'N/A'
        user = result.get('username', 'N/A') or 'N/A'
        etype = result['event_type']
        desc = result['description']
        print('  ' + etype + ': ' + desc + ' (ip=' + str(ip) + ', user=' + str(user) + ')')
    else:
        print('  FAIL: ' + line[:50])

print()
total = len(typed_events)
print('Total typed events: ' + str(total))
event_types = set(e['event_type'] for e in typed_events)
print('Event types present: ' + str(event_types))

# Kill chain verification
print()
has_failure = 'ssh_login_failure' in event_types
has_success = 'ssh_login_success' in event_types or 'root_login' in event_types
has_sudo = 'sudo_usage' in event_types
print('Has ssh_login_failure: ' + str(has_failure))
print('Has ssh_login_success/root_login: ' + str(has_success))
print('Has sudo_usage: ' + str(has_sudo))
if has_failure and has_success and has_sudo:
    print('PASS: Full kill chain events present')
else:
    print('FAIL: Missing events for full kill chain')

# MITRE mapping
print()
from app.services.mitre import EVENT_MITRE_MAP
print('=== MITRE mapping ===')
for etype in ['ssh_login_failure', 'ssh_login_success', 'sudo_usage']:
    mapping = EVENT_MITRE_MAP.get(etype)
    if mapping:
        print('  ' + etype + ' -> ' + mapping['technique_id'] + ' (' + mapping['tactic'] + '): ' + mapping['name'])
    else:
        print('  ' + etype + ' -> NO MAPPING')

# Timeline chain title
print()
from app.services.timeline import _chain_title, _chain_confidence
types = ['ssh_login_failure'] * 12 + ['ssh_login_success'] + ['sudo_usage']
title = _chain_title(types)
print('Chain title: ' + title)

class FakeEvent:
    def __init__(self, event_type):
        self.event_type = event_type
        self.timestamp = __import__('datetime').datetime.now(__import__('datetime').timezone.utc)

events = [FakeEvent(e) for e in types]
confidence = _chain_confidence(events)
print('Chain confidence: ' + str(confidence) + '/100')