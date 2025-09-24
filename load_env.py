#!/usr/bin/env python3
"""
Simple environment variable loader for local development.
This script loads variables from a .env file if it exists.
"""

import os
from pathlib import Path

def load_env_file():
    """Load environment variables from .env file if it exists."""
    env_file = Path('.env')
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
        print("Loaded environment variables from .env file")
    else:
        print("No .env file found, using system environment variables")

if __name__ == "__main__":
    load_env_file()
