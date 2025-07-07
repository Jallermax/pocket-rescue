#!/usr/bin/env python3
"""
Pocket Rescue - Master script for preserving Pocket articles.
Simple wrapper that imports the main CLI functionality from the package.
"""

import sys
from pathlib import Path

# Add the current directory to Python path for package imports
sys.path.insert(0, str(Path(__file__).parent))

def main():
    """Main entry point that delegates to the CLI package."""
    try:
        from pocket_rescue.cli.main import main as cli_main
        cli_main()
    except ImportError as e:
        print(f"ERROR: Failed to import CLI module: {e}")
        print("Please ensure the pocket_rescue package is properly installed.")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()