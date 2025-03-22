#!/usr/bin/env python3
import argparse
import os
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

        # Set up git hooks path to include our auto-fix script
        pre_commit_path = os.path.join(os.getcwd(), ".git", "hooks", "pre-commit")

        # Ensure the auto-fix script is referenced in the pre-commit hook
        with open(pre_commit_path) as f:
            content = f.read()

        # Add our custom script to automatically stage fixed files
        if "/.pre-commit" not in content:
            with open(pre_commit_path, "a") as f:
                f.write(
                    "\n# Auto-stage fixed files\n$(git rev-parse --show-toplevel)/.pre-commit\n"
                )

        # Update pre-commit hooks to the latest versions
        subprocess.run(["pre-commit", "autoupdate"], check=True)

        print("\n✅ Pre-commit hooks successfully installed!")
        print("\nPre-commit is now configured to automatically:")
        print("  1. Fix formatting and linting issues in your code")
        print("  2. Stage the fixed files")
        print("  3. Allow the commit to proceed")
        print("\nYou can still manually format all files with:")
        print("  pre-commit run --all-files")
        print("\nOr fix all issues directly with Ruff:")
        print("  python setup_precommit.py --fix-all")

    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error setting up pre-commit hooks: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1

    return 0


def fix_all_files():
    """Run Ruff to fix all files in the project."""
    print("Running Ruff to fix all issues in the codebase...")
    try:
        # Run ruff to fix all issues
        subprocess.run(["ruff", "check", "--fix", "--unsafe-fixes", "."], check=True)
        # Run ruff formatter
        subprocess.run(["ruff", "format", "."], check=True)

        print("\n✅ All files formatted and issues fixed by Ruff!")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error fixing files with Ruff: {e}")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Set up pre-commit hooks and format code")
    parser.add_argument(
        "--fix-all", action="store_true", help="Run Ruff to fix all issues in all files"
    )

    args = parser.parse_args()

    if args.fix_all:
        sys.exit(fix_all_files())
    else:
        sys.exit(setup_precommit())
