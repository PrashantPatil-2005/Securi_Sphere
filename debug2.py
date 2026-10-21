import requests
import json

r = requests.get('http://127.0.0.1:8000/openapi.json', timeout=5)
data = r.json()

# List all paths
paths = list(data.get('paths', {}).keys())
print(f'Total paths: {len(paths)}')
auth_paths = [p for p in paths if 'auth' in p.lower() or 'login' in p.lower()]
print('Auth/login paths:', auth_paths)

# Show login-related
for path in paths:
    if 'login' in path.lower():
        print(f'\nPath: {path}')
        methods = data['paths'][path]
        for method, details in methods.items():
            print(f'  {method}:')
            print(f'    {json.dumps(details, indent=6)[:500]}')