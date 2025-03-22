#!/usr/bin/env python3
import subprocess
import sys


def setup_precommit():
    """Set up pre-commit hooks for the project."""
    print("Setting up pre-commit hooks...")
    
    try:
        # Install pre-commit if not already installed
        subprocess.run([sys.executable, "-m", "pip", "install", "pre-commit"], check=True)
        
        # Install the pre-commit hooks
        subprocess.run(["pre-commit", "install"], check=True)
        
        # Update pre-commit hooks to the latest versions
        subprocess.run(["pre-commit", "autoupdate"], check=True)
        
        print("\n✅ Pre-commit hooks successfully installed!")
        print("\nYou can now format all existing files with:")
        print("    pre-commit run --all-files")
        print("\nPre-commit will automatically run on future git commits.")
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error setting up pre-commit hooks: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(setup_precommit()) 