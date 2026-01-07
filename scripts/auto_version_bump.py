#!/usr/bin/env python3
"""
Auto Version Bump Script

Automatically bumps the version when feature count threshold is met.

Rules:
- 8+ features/changes → bump patch version (e.g., 1.2.3 → 1.2.4)
- 20+ features → bump minor version (e.g., 1.2.4 → 1.3.0)
- Major breaking changes → bump major (manual)

Usage:
    python scripts/auto_version_bump.py --check     # Check if bump needed
    python scripts/auto_version_bump.py --bump      # Bump version
    python scripts/auto_version_bump.py --features 10  # Specify feature count
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Tuple, List

# Configuration
FEATURE_THRESHOLD_PATCH = 8   # Bump patch version after 8+ features
FEATURE_THRESHOLD_MINOR = 20  # Bump minor version after 20+ features

# Files containing version info
VERSION_FILES = {
    "src/api/main.py": r'APP_VERSION = "(\d+\.\d+\.\d+)"',
    "desktop/src-tauri/tauri.conf.json": r'"version": "(\d+\.\d+\.\d+)"',
    "frontend/package.json": r'"version": "(\d+\.\d+\.\d+)"',
}

# Build workflow files with DMG names
BUILD_WORKFLOWS = [
    ".github/workflows/build-release.yml",
    ".github/workflows/build-legacy-mac.yml",
]


def get_project_root() -> Path:
    """Get the project root directory."""
    script_dir = Path(__file__).parent
    return script_dir.parent


def get_current_version() -> str:
    """Get current version from main.py."""
    root = get_project_root()
    main_py = root / "src" / "api" / "main.py"
    
    content = main_py.read_text()
    match = re.search(r'APP_VERSION = "(\d+\.\d+\.\d+)"', content)
    
    if match:
        return match.group(1)
    
    raise ValueError("Could not find APP_VERSION in main.py")


def parse_version(version: str) -> Tuple[int, int, int]:
    """Parse version string into tuple."""
    parts = version.split(".")
    return int(parts[0]), int(parts[1]), int(parts[2])


def bump_version(version: str, bump_type: str = "patch") -> str:
    """Bump version based on type."""
    major, minor, patch = parse_version(version)
    
    if bump_type == "major":
        return f"{major + 1}.0.0"
    elif bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    else:  # patch
        return f"{major}.{minor}.{patch + 1}"


def count_features_since_last_tag() -> int:
    """Count feature commits since last tag."""
    try:
        # Get commits since last tag
        result = subprocess.run(
            ["git", "log", "--oneline", "--since", "1 week ago"],
            capture_output=True,
            text=True,
            cwd=get_project_root()
        )
        
        commits = result.stdout.strip().split("\n")
        
        # Count feature-related commits
        feature_keywords = [
            "feat:", "feature:", "add:", "new:", "implement:",
            "fix:", "enhance:", "improve:", "update:",
        ]
        
        feature_count = 0
        for commit in commits:
            commit_lower = commit.lower()
            for keyword in feature_keywords:
                if keyword in commit_lower:
                    feature_count += 1
                    break
        
        return feature_count
        
    except Exception as e:
        print(f"Warning: Could not count commits: {e}")
        return 0


def update_version_in_file(filepath: Path, old_version: str, new_version: str) -> bool:
    """Update version in a single file."""
    try:
        content = filepath.read_text()
        updated = content.replace(old_version, new_version)
        
        if content != updated:
            filepath.write_text(updated)
            print(f"  ✓ Updated {filepath.name}")
            return True
        else:
            print(f"  - No changes in {filepath.name}")
            return False
            
    except Exception as e:
        print(f"  ✗ Error updating {filepath.name}: {e}")
        return False


def update_all_versions(old_version: str, new_version: str):
    """Update version in all relevant files."""
    root = get_project_root()
    
    print(f"\nUpdating version: {old_version} → {new_version}")
    print("-" * 40)
    
    updated_count = 0
    
    # Update main version files
    for filepath_str, pattern in VERSION_FILES.items():
        filepath = root / filepath_str
        if filepath.exists():
            if update_version_in_file(filepath, old_version, new_version):
                updated_count += 1
    
    # Update build workflows (DMG names)
    for workflow_path in BUILD_WORKFLOWS:
        filepath = root / workflow_path
        if filepath.exists():
            if update_version_in_file(filepath, old_version, new_version):
                updated_count += 1
    
    # Update HelpModal changelog
    help_modal = root / "frontend" / "src" / "components" / "HelpModal.tsx"
    if help_modal.exists():
        content = help_modal.read_text()
        # Check if new version already has an entry
        if f"version: '{new_version}'" not in content:
            print(f"\n⚠️  Remember to add changelog entry for v{new_version} in HelpModal.tsx")
    
    print("-" * 40)
    print(f"Updated {updated_count} files")
    
    return updated_count > 0


def determine_bump_type(feature_count: int) -> str:
    """Determine what type of version bump is needed."""
    if feature_count >= FEATURE_THRESHOLD_MINOR:
        return "minor"
    elif feature_count >= FEATURE_THRESHOLD_PATCH:
        return "patch"
    else:
        return "none"


def main():
    parser = argparse.ArgumentParser(description="Auto version bump based on feature count")
    parser.add_argument("--check", action="store_true", help="Check if version bump is needed")
    parser.add_argument("--bump", action="store_true", help="Perform version bump")
    parser.add_argument("--features", type=int, help="Specify feature count manually")
    parser.add_argument("--type", choices=["patch", "minor", "major"], help="Force bump type")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be changed")
    
    args = parser.parse_args()
    
    current_version = get_current_version()
    print(f"Current version: {current_version}")
    
    # Get feature count
    if args.features is not None:
        feature_count = args.features
    else:
        feature_count = count_features_since_last_tag()
    
    print(f"Feature count: {feature_count}")
    print(f"Threshold for patch bump: {FEATURE_THRESHOLD_PATCH}")
    print(f"Threshold for minor bump: {FEATURE_THRESHOLD_MINOR}")
    
    # Determine bump type
    if args.type:
        bump_type = args.type
    else:
        bump_type = determine_bump_type(feature_count)
    
    if args.check:
        if bump_type != "none":
            print(f"\n✓ Version bump recommended: {bump_type}")
            new_version = bump_version(current_version, bump_type)
            print(f"  New version would be: {new_version}")
            return 0
        else:
            print(f"\n- No version bump needed ({feature_count} features < {FEATURE_THRESHOLD_PATCH} threshold)")
            return 0
    
    if args.bump or args.type:
        if bump_type == "none" and not args.type:
            print(f"\n- Not enough features for auto-bump ({feature_count} < {FEATURE_THRESHOLD_PATCH})")
            print("  Use --type patch/minor/major to force a bump")
            return 1
        
        new_version = bump_version(current_version, bump_type)
        
        if args.dry_run:
            print(f"\n[DRY RUN] Would bump to: {new_version}")
            return 0
        
        if update_all_versions(current_version, new_version):
            print(f"\n✓ Version bumped to {new_version}")
            print("\nNext steps:")
            print(f"  1. Add changelog entry in HelpModal.tsx")
            print(f"  2. git add -A && git commit -m 'chore: Bump version to {new_version}'")
            print(f"  3. git tag -a v{new_version} -m 'Release v{new_version}'")
            print(f"  4. git push origin main --tags")
            return 0
        else:
            print("\n✗ No files were updated")
            return 1
    
    # Default: show status
    print(f"\nUse --check to see if bump is needed, --bump to perform bump")
    return 0


if __name__ == "__main__":
    sys.exit(main())


