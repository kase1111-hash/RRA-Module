#!/usr/bin/env python3
"""
License verification script for RRA Module.

This script verifies that:
1. All Python source files have proper SPDX license headers
2. LICENSE.md file exists and is valid
3. All files reference the correct license

SPDX-License-Identifier: FSL-1.1-ALv2
Copyright 2025 Kase Branham
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Tuple

# Expected license information
EXPECTED_SPDX = "SPDX-License-Identifier: FSL-1.1-ALv2"
EXPECTED_COPYRIGHT = "Copyright 2025 Kase Branham"
EXPECTED_LICENSE_FILE = "LICENSE.md"


class LicenseVerifier:
    """Verifies license compliance across the repository."""

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.stats: Dict[str, int] = {
            "total_files": 0,
            "compliant_files": 0,
            "missing_spdx": 0,
            "missing_copyright": 0,
        }

    def verify_license_file(self) -> bool:
        """Verify that LICENSE.md exists and contains expected content."""
        print("Checking LICENSE.md file...")

        license_path = self.repo_root / EXPECTED_LICENSE_FILE
        if not license_path.exists():
            self.errors.append(f"LICENSE.md not found at {license_path}")
            return False

        try:
            with open(license_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check for key components
            checks = [
                ("FSL-1.1-ALv2", "FSL-1.1-ALv2 identifier"),
                ("Functional Source License", "License name"),
                ("Copyright 2025 Kase Branham", "Copyright notice"),
                ("Apache License, Version 2.0", "Future license grant"),
            ]

            all_passed = True
            for search_str, description in checks:
                if search_str in content:
                    print(f"  ✓ {description} found")
                else:
                    self.errors.append(f"LICENSE.md missing: {description}")
                    print(f"  ✗ {description} NOT found")
                    all_passed = False

            return all_passed

        except Exception as e:
            self.errors.append(f"Error reading LICENSE.md: {str(e)}")
            return False

    def verify_file_header(self, file_path: Path) -> Tuple[bool, str]:
        """
        Verify that a file has proper license header.

        Returns:
            Tuple of (is_compliant: bool, message: str)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                # Read first 20 lines (header should be at the top)
                lines = [next(f, '') for _ in range(20)]
                header_content = ''.join(lines)

            has_spdx = EXPECTED_SPDX in header_content
            has_copyright = EXPECTED_COPYRIGHT in header_content

            if has_spdx and has_copyright:
                return True, "Compliant"
            elif has_spdx and not has_copyright:
                self.stats["missing_copyright"] += 1
                return False, "Missing copyright notice"
            elif not has_spdx and has_copyright:
                self.stats["missing_spdx"] += 1
                return False, "Missing SPDX identifier"
            else:
                self.stats["missing_spdx"] += 1
                self.stats["missing_copyright"] += 1
                return False, "Missing both SPDX and copyright"

        except Exception as e:
            return False, f"Error: {str(e)}"

    def find_python_files(self) -> List[Path]:
        """Find all Python files that should have license headers."""
        python_files = []
        exclude_dirs = {'.git', '__pycache__', '.venv', 'venv', 'env', 'node_modules', '.pytest_cache'}

        for root, dirs, files in os.walk(self.repo_root):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]

            for file in files:
                if file.endswith('.py'):
                    python_files.append(Path(root) / file)

        return sorted(python_files)

    def verify_source_files(self) -> bool:
        """Verify all source files have proper headers."""
        print("\nChecking Python source files...")

        python_files = self.find_python_files()
        self.stats["total_files"] = len(python_files)

        print(f"Found {len(python_files)} Python files")
        print()

        all_compliant = True
        non_compliant_files = []

        for file_path in python_files:
            rel_path = file_path.relative_to(self.repo_root)
            is_compliant, message = self.verify_file_header(file_path)

            if is_compliant:
                self.stats["compliant_files"] += 1
            else:
                all_compliant = False
                non_compliant_files.append((rel_path, message))

        # Report results
        if all_compliant:
            print(f"✓ All {len(python_files)} files are compliant")
        else:
            print(f"✗ {len(non_compliant_files)} files are NOT compliant:")
            print()
            for file_path, message in non_compliant_files:
                print(f"  - {file_path}: {message}")
                self.errors.append(f"{file_path}: {message}")

        return all_compliant

    def verify_documentation(self) -> bool:
        """Verify that key documentation files reference the license."""
        print("\nChecking documentation files...")

        docs_to_check = ["README.md", "CONTRIBUTING.md"]
        all_compliant = True

        for doc_file in docs_to_check:
            doc_path = self.repo_root / doc_file
            if not doc_path.exists():
                self.warnings.append(f"{doc_file} not found (optional)")
                print(f"  - {doc_file}: Not found (optional)")
                continue

            try:
                with open(doc_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Check if LICENSE is mentioned
                if "LICENSE" in content or "license" in content.lower():
                    print(f"  ✓ {doc_file} references license")
                else:
                    self.warnings.append(f"{doc_file} does not mention license")
                    print(f"  ! {doc_file} does not mention license")

            except Exception as e:
                self.warnings.append(f"Error reading {doc_file}: {str(e)}")

        return all_compliant

    def print_summary(self) -> None:
        """Print verification summary."""
        print("\n" + "=" * 70)
        print("LICENSE VERIFICATION SUMMARY")
        print("=" * 70)
        print()

        print("Statistics:")
        print(f"  Total Python files:    {self.stats['total_files']}")
        print(f"  Compliant files:       {self.stats['compliant_files']}")
        print(f"  Missing SPDX:          {self.stats['missing_spdx']}")
        print(f"  Missing Copyright:     {self.stats['missing_copyright']}")
        print()

        if self.errors:
            print(f"Errors ({len(self.errors)}):")
            for error in self.errors:
                print(f"  ✗ {error}")
            print()

        if self.warnings:
            print(f"Warnings ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  ! {warning}")
            print()

        # Overall result
        if not self.errors:
            print("✓ LICENSE VERIFICATION PASSED")
            print()
            print("All files are properly licensed under FSL-1.1-ALv2")
            print("GitHub work is correctly linked to the license")
        else:
            print("✗ LICENSE VERIFICATION FAILED")
            print()
            print("Please fix the errors listed above")

        print("=" * 70)

    def verify(self) -> bool:
        """
        Run full license verification.

        Returns:
            True if all checks pass, False otherwise
        """
        print("=" * 70)
        print("RRA Module - License Verification")
        print("=" * 70)
        print()

        license_ok = self.verify_license_file()
        sources_ok = self.verify_source_files()
        self.verify_documentation()

        self.print_summary()

        return license_ok and sources_ok and len(self.errors) == 0


def main():
    """Main function."""
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent

    verifier = LicenseVerifier(repo_root)
    success = verifier.verify()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
