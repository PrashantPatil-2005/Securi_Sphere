import requests
import json

r = requests.get('http://127.0.0.1:8000/openapi.json', timeout=5)
data = r.json()

# Find login endpoint
login_path = None
for path, methods in data.get('paths', {}).items():
    if 'login' in path.lower() or 'auth' in path.lower():
        login_path = path
        break

print('Auth path:', login_path)
if login_path:
    methods = data['paths'][login_path]
    for method, details in methods.items():
        content = details.get('requestBody', {}).get('content', {})
        print(f'  {method}: {list(content.keys()) if content else "no requestBody"}')
        if content:
            for ct, ct_details in content.items():
                schema = ct_details.get('schema', {})
                skeys = schema.keys() if schema else "no schema"
                print(f'    schema keys: {list(skeys) if isinstance(skeys, dict) else skeys}')