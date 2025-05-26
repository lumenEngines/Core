#!/usr/bin/env python3
"""Test script to verify imports without GUI dependencies."""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("Testing imports...")

try:
    from core.logger_config import setup_logging
    print("✓ logger_config imported")
    
    from core.config import config
    print("✓ config imported")
    
    from core import prompting
    print("✓ prompting imported")
    
    from api.api_exceptions import APIError
    print("✓ api_exceptions imported")
    
    # Test if we can initialize logging
    setup_logging()
    print("✓ Logging initialized")
    
    # Test config
    print(f"✓ Config validated: {config.validate()}")
    
    print("\nAll core imports working! The application structure is correct.")
    print("\nTo run the full application:")
    print("1. Install dependencies: pip install -r requirements.txt")
    print("2. Set up .env file with your API keys")
    print("3. Run: python main.py")
    
except ImportError as e:
    print(f"✗ Import error: {e}")
except Exception as e:
    print(f"✗ Error: {e}")