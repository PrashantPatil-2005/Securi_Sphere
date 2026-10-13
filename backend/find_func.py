import os
os.chdir('app/services/correlation_engine.py')
with open('correlation_engine.py', 'r') as f:
    lines = f.readlines()
for i, line in enumerate(lines, 1):
    if 'seed_correlation_rules' in line:
        start = max(0, i-5)
        end = min(len(lines), i+80)
        for j in range(start, end):
            print(f'{j+1}: {lines[j]}', end='')
        print('---')
        break
os.chdir('../../../..')