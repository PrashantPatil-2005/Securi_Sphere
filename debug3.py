import requests
import json

r = requests.get('http://127.0.0.1:8000/openapi.json', timeout=5)
data = r.json()

# Find LoginRequest schema
schemas = data.get('components', {}).get('schemas', {})
for name, schema in schemas.items():
    if 'login' in name.lower() or 'Login' in name:
        print(f'Schema: {name}')
        print(json.dumps(schema, indent=2))
        print('---')