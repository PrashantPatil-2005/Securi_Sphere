with open('app/services/offense_engine.py', 'r') as f:
    lines = f.readlines()
for i, line in enumerate(lines, 1):
    if 'find_or_create_offense' in line:
        for j in range(i-1, min(len(lines), i+30)):
            print(f'{j+1}: {lines[j]}', end='')
        print('---')
        break
import os
os.chdir('../../../..')