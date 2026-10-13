import os

for root, dirs, files in os.walk('app/services/correlation'):
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            with open(path) as fh:
                content = fh.read()
                if 'matched.rule_name' in content:
                    print(f'=== {path} ===')
                    for i, line in enumerate(content.split('\n'), 1):
                        if 'rule_name' in line:
                            print(f'  {i}: {line}')
                    # Fix the rule_name reference
                    old = 'matched.rule_name or rule.name'
                    new = 'matched.description or rule.description or "Correlation matched"'
                    if old in content:
                        content = content.replace(old, new)
                        with open(path, 'w') as wf:
                            wf.write(content)
                        print(f'Fixed: replaced "{old}" with "{new}"')