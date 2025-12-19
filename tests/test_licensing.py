# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Tests for license compliance and verification.

This test suite ensures that the licensing system is working correctly
and that all GitHub work is properly linked to the FSL-1.1-ALv2 license.
"""

import unittest
from pathlib import Path
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestLicenseCompliance(unittest.TestCase):
    """Test suite for license compliance verification."""

    def setUp(self):
        """Set up test fixtures."""
        self.repo_root = Path(__file__).parent.parent
        self.license_file = self.repo_root / "LICENSE.md"

    def test_license_file_exists(self):
        """Test that LICENSE.md file exists."""
        self.assertTrue(
            self.license_file.exists(),
            "LICENSE.md file must exist in repository root"
        )

    def test_license_contains_fsl(self):
        """Test that LICENSE.md contains FSL-1.1-ALv2 identifier."""
        with open(self.license_file, 'r', encoding='utf-8') as f:
            content = f.read()

        self.assertIn(
            "FSL-1.1-ALv2",
            content,
            "LICENSE.md must contain FSL-1.1-ALv2 identifier"
        )

    def test_license_contains_copyright(self):
        """Test that LICENSE.md contains copyright notice."""
        with open(self.license_file, 'r', encoding='utf-8') as f:
            content = f.read()

        self.assertIn(
            "Copyright 2025 Kase Branham",
            content,
            "LICENSE.md must contain copyright notice"
        )

    def test_license_contains_future_grant(self):
        """Test that LICENSE.md contains Apache 2.0 future grant."""
        with open(self.license_file, 'r', encoding='utf-8') as f:
            content = f.read()

        self.assertIn(
            "Apache License, Version 2.0",
            content,
            "LICENSE.md must contain Apache 2.0 future license grant"
        )

    def test_source_files_have_headers(self):
        """Test that all Python source files have proper license headers."""
        src_dir = self.repo_root / "src"
        if not src_dir.exists():
            self.skipTest("src directory not found")

        python_files = list(src_dir.rglob("*.py"))
        self.assertGreater(len(python_files), 0, "Should find Python files in src/")

        files_without_headers = []
        for py_file in python_files:
            with open(py_file, 'r', encoding='utf-8') as f:
                # Read first 10 lines
                first_lines = ''.join([next(f, '') for _ in range(10)])

            if "SPDX-License-Identifier" not in first_lines:
                files_without_headers.append(py_file.relative_to(self.repo_root))

        self.assertEqual(
            len(files_without_headers),
            0,
            f"Files without license headers: {files_without_headers}"
        )

    def test_examples_have_headers(self):
        """Test that example files have proper license headers."""
        examples_dir = self.repo_root / "examples"
        if not examples_dir.exists():
            self.skipTest("examples directory not found")

        python_files = list(examples_dir.rglob("*.py"))
        if len(python_files) == 0:
            self.skipTest("No Python files in examples/")

        for py_file in python_files:
            with open(py_file, 'r', encoding='utf-8') as f:
                first_lines = ''.join([next(f, '') for _ in range(10)])

            self.assertIn(
                "SPDX-License-Identifier",
                first_lines,
                f"Example file {py_file} missing license header"
            )

    def test_scripts_have_headers(self):
        """Test that script files have proper license headers."""
        scripts_dir = self.repo_root / "scripts"
        if not scripts_dir.exists():
            self.skipTest("scripts directory not found")

        python_files = list(scripts_dir.rglob("*.py"))
        if len(python_files) == 0:
            self.skipTest("No Python files in scripts/")

        for py_file in python_files:
            with open(py_file, 'r', encoding='utf-8') as f:
                first_lines = ''.join([next(f, '') for _ in range(10)])

            self.assertIn(
                "SPDX-License-Identifier",
                first_lines,
                f"Script file {py_file} missing license header"
            )

    def test_verification_script_exists(self):
        """Test that license verification script exists."""
        verify_script = self.repo_root / "scripts" / "verify_license.py"
        self.assertTrue(
            verify_script.exists(),
            "License verification script must exist"
        )

    def test_github_workflow_exists(self):
        """Test that GitHub Actions license verification workflow exists."""
        workflow_file = self.repo_root / ".github" / "workflows" / "license-verification.yml"
        self.assertTrue(
            workflow_file.exists(),
            "GitHub Actions license verification workflow must exist"
        )

    def test_licensing_documentation_exists(self):
        """Test that LICENSING.md documentation exists."""
        licensing_doc = self.repo_root / "LICENSING.md"
        self.assertTrue(
            licensing_doc.exists(),
            "LICENSING.md documentation must exist"
        )


class TestSPDXHeaders(unittest.TestCase):
    """Test suite for SPDX header format compliance."""

    EXPECTED_SPDX = "SPDX-License-Identifier: FSL-1.1-ALv2"
    EXPECTED_COPYRIGHT = "Copyright 2025 Kase Branham"

    def setUp(self):
        """Set up test fixtures."""
        self.repo_root = Path(__file__).parent.parent

    def test_spdx_format(self):
        """Test that SPDX headers follow correct format."""
        test_file = Path(__file__)

        with open(test_file, 'r', encoding='utf-8') as f:
            first_lines = ''.join([next(f, '') for _ in range(5)])

        # Check for proper SPDX format
        self.assertIn(self.EXPECTED_SPDX, first_lines)
        self.assertIn(self.EXPECTED_COPYRIGHT, first_lines)

    def test_spdx_placement(self):
        """Test that SPDX headers are placed at the top of files."""
        test_file = Path(__file__)

        with open(test_file, 'r', encoding='utf-8') as f:
            lines = [next(f, '') for _ in range(10)]

        # SPDX should appear in first few lines (after shebang/encoding)
        found_in_first_5 = any(self.EXPECTED_SPDX in line for line in lines[:5])
        self.assertTrue(
            found_in_first_5,
            "SPDX header should appear in first 5 lines"
        )


class TestLicenseIntegration(unittest.TestCase):
    """Test suite for license system integration."""

    def setUp(self):
        """Set up test fixtures."""
        self.repo_root = Path(__file__).parent.parent

    def test_can_import_verify_script(self):
        """Test that license verification script can be imported."""
        scripts_path = self.repo_root / "scripts"
        sys.path.insert(0, str(scripts_path))

        try:
            # Import should work without errors
            import verify_license
            self.assertTrue(hasattr(verify_license, 'LicenseVerifier'))
        except ImportError as e:
            self.fail(f"Failed to import verify_license: {e}")
        finally:
            sys.path.remove(str(scripts_path))

    def test_verification_runs_successfully(self):
        """Test that license verification can run."""
        verify_script = self.repo_root / "scripts" / "verify_license.py"

        # Run verification script
        exit_code = os.system(f"python {verify_script} > /dev/null 2>&1")

        self.assertEqual(
            exit_code,
            0,
            "License verification script should exit with code 0"
        )


def run_license_tests():
    """Run all license compliance tests."""
    print("=" * 70)
    print("Running License Compliance Tests")
    print("=" * 70)
    print()

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestLicenseCompliance))
    suite.addTests(loader.loadTestsFromTestCase(TestSPDXHeaders))
    suite.addTests(loader.loadTestsFromTestCase(TestLicenseIntegration))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print()
    print("=" * 70)
    if result.wasSuccessful():
        print("✓ ALL LICENSE COMPLIANCE TESTS PASSED")
        print()
        print("GitHub work is properly linked to FSL-1.1-ALv2 license")
    else:
        print("✗ SOME TESTS FAILED")
        print()
        print("Please review failures above")
    print("=" * 70)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_license_tests()
    sys.exit(0 if success else 1)
