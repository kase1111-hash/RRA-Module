#!/usr/bin/env python3
"""
Script to add SPDX license headers to all Python source files.

SPDX-License-Identifier: FSL-1.1-ALv2
Copyright 2025 Kase Branham
"""

import os
from pathlib import Path
from typing import List, Tuple

# License header template
LICENSE_HEADER = """# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""

# Alternative header for files that start with shebang
LICENSE_HEADER_AFTER_SHEBANG = """#
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""


def has_license_header(content: str) -> bool:
    """Check if file already has a license header."""
    return "SPDX-License-Identifier" in content or "Copyright 2025 Kase Branham" in content


def add_header_to_file(file_path: Path) -> Tuple[bool, str]:
    """
    Add license header to a Python file.

    Returns:
        Tuple of (modified: bool, message: str)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Skip if already has license header
        if has_license_header(content):
            return False, "Already has license header"

        # Determine where to insert header
        lines = content.split('\n')

        if not lines:
            return False, "Empty file"

        # Check for shebang
        has_shebang = lines[0].startswith('#!')

        # Build new content
        new_lines = []

        if has_shebang:
            # Add shebang first, then license header
            new_lines.append(lines[0])
            new_lines.extend(LICENSE_HEADER_AFTER_SHEBANG.rstrip('\n').split('\n'))

            # Add rest of content (skip first line since it's the shebang)
            if len(lines) > 1:
                new_lines.extend(lines[1:])
        else:
            # Add license header first
            new_lines.extend(LICENSE_HEADER.rstrip('\n').split('\n'))

            # Add original content
            new_lines.extend(lines)

        # Write back to file
        new_content = '\n'.join(new_lines)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        return True, "Header added"

    except Exception as e:
        return False, f"Error: {str(e)}"


def find_python_files(root_dir: Path) -> List[Path]:
    """Find all Python files in the repository."""
    python_files = []

    # Exclude certain directories
    exclude_dirs = {'.git', '__pycache__', '.venv', 'venv', 'env', 'node_modules', '.pytest_cache'}

    for root, dirs, files in os.walk(root_dir):
        # Remove excluded directories from search
        dirs[:] = [d for d in dirs if d not in exclude_dirs]

        for file in files:
            if file.endswith('.py'):
                python_files.append(Path(root) / file)

    return sorted(python_files)


def main():
    """Main function."""
    print("=" * 70)
    print("RRA Module - License Header Addition Tool")
    print("=" * 70)
    print()

    # Get repository root (parent of scripts directory)
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent

    print(f"Repository root: {repo_root}")
    print()

    # Find all Python files
    print("Finding Python files...")
    python_files = find_python_files(repo_root)
    print(f"Found {len(python_files)} Python files")
    print()

    # Process each file
    modified_count = 0
    skipped_count = 0
    error_count = 0

    print("Processing files:")
    print("-" * 70)

    for file_path in python_files:
        rel_path = file_path.relative_to(repo_root)
        modified, message = add_header_to_file(file_path)

        if modified:
            print(f"✓ {rel_path}: {message}")
            modified_count += 1
        elif "Error" in message:
            print(f"✗ {rel_path}: {message}")
            error_count += 1
        else:
            print(f"- {rel_path}: {message}")
            skipped_count += 1

    print("-" * 70)
    print()
    print("Summary:")
    print(f"  Modified: {modified_count}")
    print(f"  Skipped:  {skipped_count}")
    print(f"  Errors:   {error_count}")
    print(f"  Total:    {len(python_files)}")
    print()
    print("=" * 70)


if __name__ == "__main__":
    main()
