#!/usr/bin/env python
import sys
import os
import subprocess

# Add backend to path
sys.path.insert(0, r'C:\Users\Prash\Desktop\Securi\backend')

# Change to backend directory
os.chdir(r'C:\Users\Prash\Desktop\Securi\backend')

# Run uvicorn as main process
if __name__ == "__main__":
    subprocess.run([
        sys.executable, '-m', 'uvicorn',
        'app.main:app',
        '--reload',
        '--host', '0.0.0.0',
        '--port', '8000'
    ])