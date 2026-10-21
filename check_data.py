import requests

token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJiNzk0NTQzZC03ZWY0LTQ1ZGMtOGQ0MC1hN2E0MGI3NDc1ZTEiLCJyb2xlIjoiYWRtaW4iLCJ0eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzkxOTQzNTA0fQ.N3DkHJRnkwLdcswA0gxxQWmr6Heq5TDXPe4midlSyYo'

r = requests.get('http://127.0.0.1:8000/api/v1/alerts/', headers={'Authorization': f'Bearer {token}'}, timeout=5)
data = r.json()
print('Alert count:', data.get('total', 0))
print('Items on page:', len(data.get('items', [])))
for a in data.get('items', [])[:3]:
    print(f"  ID: {a.get('id')}, Title: {a.get('title')}, Severity: {a.get('severity')}, Status: {a.get('status')}")