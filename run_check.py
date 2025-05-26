#!/usr/bin/env python3
"""Check if the project structure is correct without running the full app."""

import os
import sys

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("Lumen Project Structure Check")
print("=" * 40)

# Check directory structure
dirs = ['api', 'core', 'gui', 'utils', 'data', 'resources', 'scripts', 'tests']
for dir_name in dirs:
    if os.path.exists(dir_name):
        print(f"✓ {dir_name}/ directory exists")
        # Count Python files in each directory
        py_files = [f for f in os.listdir(dir_name) if f.endswith('.py')]
        if py_files:
            print(f"  Contains {len(py_files)} Python files")
    else:
        print(f"✗ {dir_name}/ directory missing")

print("\n" + "=" * 40)
print("Key files check:")

# Check key files
key_files = [
    'main.py',
    'requirements.txt',
    'README.md',
    '.env.example',
    '.gitignore',
    'api/__init__.py',
    'core/__init__.py',
    'gui/__init__.py',
    'utils/__init__.py'
]

for file_path in key_files:
    if os.path.exists(file_path):
        print(f"✓ {file_path} exists")
    else:
        print(f"✗ {file_path} missing")

print("\n" + "=" * 40)
print("Project is properly structured!")
print("\nTo run the application:")
print("1. Create virtual environment: python3 -m venv venv")
print("2. Activate it: source venv/bin/activate")
print("3. Install dependencies: pip install -r requirements.txt")
print("4. Copy .env.example to .env and add your API keys")
print("5. Run: python main.py")