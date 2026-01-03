# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Code verification module.

Verifies that code repositories:
- Have passing tests
- Meet code quality standards (linting)
- Are free of common security issues
- Match their README descriptions
"""

import subprocess
import re
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

from rra.verification.dependency_installer import DependencyInstaller, IsolatedEnvironment


class VerificationStatus(str, Enum):
    """Verification status levels."""

    PASSED = "passed"
    WARNING = "warning"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class CheckResult:
    """Result of a single verification check."""

    name: str
    status: VerificationStatus
    message: str
    details: Optional[Dict[str, Any]] = None


@dataclass
class VerificationResult:
    """Complete verification result for a repository."""

    repo_path: str
    repo_url: str
    overall_status: VerificationStatus
    checks: List[CheckResult] = field(default_factory=list)
    score: float = 0.0  # 0-100 verification score
    verified_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "repo_path": self.repo_path,
            "repo_url": self.repo_url,
            "overall_status": self.overall_status.value,
            "checks": [
                {
                    "name": c.name,
                    "status": c.status.value,
                    "message": c.message,
                    "details": c.details,
                }
                for c in self.checks
            ],
            "score": self.score,
            "verified_at": self.verified_at,
        }


class CodeVerifier:
    """
    Verifies that code repositories meet quality and correctness standards.

    Performs the following checks:
    1. Test suite existence and execution
    2. Linting and code quality
    3. Security vulnerability scanning
    4. Build/installation verification
    5. README-to-code alignment
    """

    # Common security patterns to check for
    # Note: Patterns are designed to minimize false positives from:
    # - Enum/constant definitions (UPPER_CASE = "value")
    # - Type hints and token type names
    # - Test fixtures (handled by skipping test files)
    SECURITY_PATTERNS = {
        "hardcoded_secrets": [
            # Match lowercase variable assignments that look like real secrets
            # Excludes UPPER_CASE enum definitions and type hints
            r'(?<![A-Z_])(password|api_key|api_secret|private_key|secret_key)\s*=\s*["\'][a-zA-Z0-9_\-]{8,}["\']',
            r"(?i)aws_secret_access_key\s*=\s*['\"][A-Za-z0-9/+=]{20,}['\"]",
            r"-----BEGIN (RSA |DSA |EC )?PRIVATE KEY-----",
        ],
        "sql_injection": [
            r'execute\s*\(\s*["\'][^"\']*%s',
            r'cursor\.execute\s*\(\s*f["\']',
            r'\.query\s*\(\s*f["\'].*\{',
        ],
        "command_injection": [
            r'os\.system\s*\(\s*f["\']',
            r'subprocess\.\w+\s*\(\s*f["\']',
            r"eval\s*\(\s*(?:input|request)",
        ],
        "path_traversal": [
            # Match open() with user input, but exclude urlopen() which is for HTTP
            r"(?<!url)open\s*\(\s*(?:request|input|user)",
            r"\.\./",
        ],
    }

    # Test command patterns by language
    TEST_COMMANDS = {
        "python": ["pytest", "python -m pytest", "python -m unittest discover"],
        "javascript": ["npm test", "yarn test", "jest"],
        "typescript": ["npm test", "yarn test", "jest"],
        "rust": ["cargo test"],
        "go": ["go test ./..."],
        "java": ["mvn test", "gradle test"],
        "ruby": ["rspec", "rake test"],
    }

    # Lint command patterns by language
    LINT_COMMANDS = {
        "python": ["ruff check .", "flake8", "pylint"],
        "javascript": ["eslint .", "npm run lint"],
        "typescript": ["eslint .", "tsc --noEmit"],
        "rust": ["cargo clippy"],
        "go": ["golangci-lint run"],
    }

    def __init__(
        self,
        timeout: int = 300,
        skip_tests: bool = False,
        skip_security: bool = False,
        auto_install_deps: bool = False,
        use_cache: bool = True,
    ):
        """
        Initialize the code verifier.

        Args:
            timeout: Maximum time (seconds) for test/lint commands
            skip_tests: Skip running actual tests (just check existence)
            skip_security: Skip security pattern scanning
            auto_install_deps: Automatically install dependencies in temp environment
            use_cache: Cache virtual environments for faster subsequent runs
        """
        self.timeout = timeout
        self.skip_tests = skip_tests
        self.skip_security = skip_security
        self.auto_install_deps = auto_install_deps
        self.use_cache = use_cache
        self._dep_installer: Optional[DependencyInstaller] = None
        self._isolated_env: Optional[IsolatedEnvironment] = None

    def verify(
        self,
        repo_path: Path,
        repo_url: str = "",
        readme_content: Optional[str] = None,
    ) -> VerificationResult:
        """
        Perform complete verification of a repository.

        Args:
            repo_path: Path to the local repository
            repo_url: Original repository URL
            readme_content: README content for alignment checking

        Returns:
            VerificationResult with all check results
        """
        from datetime import datetime

        checks: List[CheckResult] = []

        # Set up isolated environment if auto_install_deps is enabled
        if self.auto_install_deps and not self.skip_tests:
            self._setup_isolated_env(repo_path)

        try:
            # 1. Check for test files
            test_check = self._check_tests(repo_path)
            checks.append(test_check)

            # 2. Check code quality (linting)
            lint_check = self._check_linting(repo_path)
            checks.append(lint_check)

            # 3. Security scan
            if not self.skip_security:
                security_check = self._check_security(repo_path)
                checks.append(security_check)

            # 4. Check build/installation
            build_check = self._check_build(repo_path)
            checks.append(build_check)

            # 5. README alignment check
            if readme_content:
                alignment_check = self._check_readme_alignment(repo_path, readme_content)
                checks.append(alignment_check)

            # 6. Check for documentation
            docs_check = self._check_documentation(repo_path)
            checks.append(docs_check)

            # 7. Check for license
            license_check = self._check_license(repo_path)
            checks.append(license_check)

            # Calculate overall status and score
            overall_status, score = self._calculate_overall(checks)

            return VerificationResult(
                repo_path=str(repo_path),
                repo_url=repo_url,
                overall_status=overall_status,
                checks=checks,
                score=score,
                verified_at=datetime.now().isoformat(),
            )
        finally:
            # Clean up isolated environment
            self._cleanup_isolated_env()

    def _setup_isolated_env(self, repo_path: Path) -> None:
        """Set up an isolated environment for dependency installation."""
        languages = self._detect_languages(repo_path)
        primary_lang = languages[0] if languages else "python"

        self._dep_installer = DependencyInstaller(
            timeout=self.timeout,
            use_cache=self.use_cache,
            parallel_tests=True,  # Enable parallel test execution
        )
        self._isolated_env = self._dep_installer.create_isolated_env(
            repo_path, language=primary_lang
        )

    def _cleanup_isolated_env(self) -> None:
        """Clean up the isolated environment."""
        if self._dep_installer:
            self._dep_installer.cleanup_all()
            self._dep_installer = None
            self._isolated_env = None

    def _check_tests(self, repo_path: Path) -> CheckResult:
        """Check for test files and optionally run them."""
        test_patterns = [
            "test_*.py",
            "*_test.py",
            "tests/*.py",
            "*.test.js",
            "*.spec.js",
            "*.test.ts",
            "*.spec.ts",
            "*_test.go",
            "*_test.rs",
        ]

        test_files = []
        for pattern in test_patterns:
            test_files.extend(repo_path.rglob(pattern))

        if not test_files:
            return CheckResult(
                name="tests",
                status=VerificationStatus.WARNING,
                message="No test files found",
                details={"test_count": 0},
            )

        # Count test functions/cases
        test_count = 0
        for tf in test_files[:50]:  # Limit for performance
            try:
                content = tf.read_text(encoding="utf-8", errors="ignore")
                # Count test functions
                test_count += len(
                    re.findall(r"(def test_|test\(|it\(|describe\(|#\[test\]|func Test)", content)
                )
            except Exception:
                pass

        if self.skip_tests:
            return CheckResult(
                name="tests",
                status=VerificationStatus.PASSED,
                message=f"Found {len(test_files)} test files with ~{test_count} test cases",
                details={"test_files": len(test_files), "test_count": test_count},
            )

        # Try to run tests
        languages = self._detect_languages(repo_path)
        test_result = self._run_tests(repo_path, languages)

        # Get summary info if available
        summary = test_result.get("summary", {})
        passed = summary.get("passed", 0)
        failed = summary.get("failed", 0)
        errors = summary.get("errors", 0)

        if test_result["success"]:
            # Build detailed message with actual counts
            if passed > 0:
                msg = f"Tests passed: {passed} passed"
                if summary.get("skipped"):
                    msg += f", {summary['skipped']} skipped"
            else:
                msg = f"Tests passed ({len(test_files)} files, ~{test_count} cases)"

            return CheckResult(
                name="tests",
                status=VerificationStatus.PASSED,
                message=msg,
                details={
                    "test_files": len(test_files),
                    "test_count": test_count,
                    "output": test_result.get("output", "")[-2000:],  # Show end of output
                    "summary": summary,
                },
            )
        elif test_result.get("timeout"):
            # Timeout is a warning, not a failure - large test suites shouldn't penalize repos
            return CheckResult(
                name="tests",
                status=VerificationStatus.WARNING,
                message=f"Tests timed out ({len(test_files)} files, ~{test_count} cases detected)",
                details={
                    "test_files": len(test_files),
                    "test_count": test_count,
                    "warning": "Test suite too large or slow; consider using --skip-tests or --timeout",
                },
            )
        elif test_result.get("dependency_error"):
            # Missing dependencies is a warning - repo has tests but can't run without install
            return CheckResult(
                name="tests",
                status=VerificationStatus.WARNING,
                message=f"Tests need dependencies ({len(test_files)} files, ~{test_count} cases detected)",
                details={
                    "test_files": len(test_files),
                    "test_count": test_count,
                    "warning": "Install dependencies to run tests; verification based on test structure",
                    "error": test_result.get("error", "")[-2000:],
                },
            )
        else:
            # Calculate pass rate if we have test counts
            total_tests = passed + failed + errors
            pass_rate = (passed / total_tests * 100) if total_tests > 0 else 0

            # Build informative message
            if passed > 0 or failed > 0:
                msg = f"Tests: {passed} passed, {failed} failed, {errors} errors"
            else:
                error_preview = test_result.get("error", "Unknown error")
                msg = f"Tests failed: {error_preview[:100]}"

            # Determine status based on pass rate
            # High pass rate (>= 95%) with few failures = WARNING (not full failure)
            # Moderate pass rate (>= 80%) = WARNING
            # Low pass rate (< 80%) = FAILED
            if total_tests > 0 and pass_rate >= 95:
                # Very high pass rate - just a warning, minor issues
                status = VerificationStatus.WARNING
                msg = f"Tests mostly passing: {passed} passed, {failed} failed ({pass_rate:.1f}% pass rate)"
            elif total_tests > 0 and pass_rate >= 80:
                # Good pass rate - warning with more urgency
                status = VerificationStatus.WARNING
                msg = f"Tests: {passed} passed, {failed} failed ({pass_rate:.1f}% pass rate)"
            else:
                # Low pass rate or no test counts - full failure
                status = VerificationStatus.FAILED

            return CheckResult(
                name="tests",
                status=status,
                message=msg,
                details={
                    "test_files": len(test_files),
                    "test_count": test_count,
                    "error": test_result.get("error", "")[-3000:],  # Show end of output
                    "summary": summary,
                    "pass_rate": pass_rate if total_tests > 0 else None,
                },
            )

    def _check_linting(self, repo_path: Path) -> CheckResult:
        """Check code quality through linting."""
        languages = self._detect_languages(repo_path)

        if not languages:
            return CheckResult(
                name="linting",
                status=VerificationStatus.SKIPPED,
                message="No supported languages detected",
            )

        # Check for linting config files
        lint_configs = [
            ".eslintrc",
            ".eslintrc.js",
            ".eslintrc.json",
            "pyproject.toml",
            "setup.cfg",
            ".flake8",
            "ruff.toml",
            "clippy.toml",
            ".golangci.yml",
        ]

        has_lint_config = any((repo_path / cfg).exists() for cfg in lint_configs)

        # Try to run linting
        lint_result = self._run_linting(repo_path, languages)

        if lint_result["success"]:
            return CheckResult(
                name="linting",
                status=VerificationStatus.PASSED,
                message="Code passes linting checks"
                + (" (config found)" if has_lint_config else ""),
                details={
                    "has_config": has_lint_config,
                    "output": lint_result.get("output", "")[:500],
                },
            )
        elif lint_result.get("skipped"):
            return CheckResult(
                name="linting",
                status=VerificationStatus.SKIPPED,
                message="Linting tools not available",
                details={"has_config": has_lint_config},
            )
        else:
            # Linting issues are warnings, not failures
            return CheckResult(
                name="linting",
                status=VerificationStatus.WARNING,
                message=f"Linting issues found: {lint_result.get('issues', 0)} issues",
                details={
                    "has_config": has_lint_config,
                    "issues": lint_result.get("issues", 0),
                    "output": lint_result.get("output", "")[:500],
                },
            )

    def _check_security(self, repo_path: Path) -> CheckResult:
        """Scan for common security issues."""
        issues: List[Dict[str, Any]] = []

        code_extensions = {".py", ".js", ".ts", ".java", ".go", ".rs", ".rb", ".php"}

        files_scanned = 0
        for file_path in repo_path.rglob("*"):
            if not file_path.is_file():
                continue
            if file_path.suffix not in code_extensions:
                continue
            if any(
                part.startswith(".")
                or part in {"node_modules", "venv", "__pycache__", "tests", "test", "docs", "examples"}
                for part in file_path.parts
            ):
                continue
            # Skip test files and examples (they often have mock/placeholder credentials)
            if file_path.name.startswith("test_") or file_path.name.endswith("_test.py"):
                continue

            files_scanned += 1
            if files_scanned > 500:  # Limit for performance
                break

            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")

                for category, patterns in self.SECURITY_PATTERNS.items():
                    for pattern in patterns:
                        matches = re.findall(pattern, content)
                        if matches:
                            issues.append(
                                {
                                    "file": str(file_path.relative_to(repo_path)),
                                    "category": category,
                                    "count": len(matches),
                                }
                            )
            except Exception:
                pass

        if not issues:
            return CheckResult(
                name="security",
                status=VerificationStatus.PASSED,
                message=f"No security issues detected ({files_scanned} files scanned)",
                details={"files_scanned": files_scanned},
            )
        else:
            # Group issues by category
            by_category = {}
            for issue in issues:
                cat = issue["category"]
                by_category[cat] = by_category.get(cat, 0) + 1

            return CheckResult(
                name="security",
                status=VerificationStatus.WARNING,
                message=f"Potential security issues found: {sum(by_category.values())} in {len(issues)} locations",
                details={
                    "files_scanned": files_scanned,
                    "issues_by_category": by_category,
                    "issues": issues[:10],  # Limit detail
                },
            )

    def _check_build(self, repo_path: Path) -> CheckResult:
        """Check if the project can be built/installed."""
        build_files = {
            "pyproject.toml": "python",
            "setup.py": "python",
            "requirements.txt": "python",
            "package.json": "javascript",
            "Cargo.toml": "rust",
            "go.mod": "go",
            "pom.xml": "java",
            "build.gradle": "java",
            "Makefile": "make",
        }

        detected_builds = []
        for filename, lang in build_files.items():
            if (repo_path / filename).exists():
                detected_builds.append({"file": filename, "language": lang})

        if not detected_builds:
            return CheckResult(
                name="build",
                status=VerificationStatus.SKIPPED,
                message="No build configuration detected",
            )

        # Try a simple build/install check
        build_result = self._try_build(repo_path, detected_builds)

        if build_result["success"]:
            return CheckResult(
                name="build",
                status=VerificationStatus.PASSED,
                message=f"Build configuration valid ({', '.join(b['language'] for b in detected_builds)})",
                details={"build_systems": detected_builds},
            )
        elif build_result.get("skipped"):
            return CheckResult(
                name="build",
                status=VerificationStatus.SKIPPED,
                message="Build tools not available for verification",
                details={"build_systems": detected_builds},
            )
        else:
            return CheckResult(
                name="build",
                status=VerificationStatus.WARNING,
                message=f"Build issues detected: {build_result.get('error', 'Unknown')[:100]}",
                details={
                    "build_systems": detected_builds,
                    "error": build_result.get("error", ""),
                },
            )

    def _check_readme_alignment(self, repo_path: Path, readme_content: str) -> CheckResult:
        """Check if code matches README claims."""
        claims = self._extract_readme_claims(readme_content)

        if not claims:
            return CheckResult(
                name="readme_alignment",
                status=VerificationStatus.SKIPPED,
                message="No verifiable claims found in README",
            )

        verified_claims = []
        unverified_claims = []

        for claim in claims:
            if self._verify_claim(repo_path, claim):
                verified_claims.append(claim)
            else:
                unverified_claims.append(claim)

        if not unverified_claims:
            return CheckResult(
                name="readme_alignment",
                status=VerificationStatus.PASSED,
                message=f"All {len(verified_claims)} README claims verified",
                details={"verified_claims": verified_claims},
            )
        elif len(verified_claims) >= len(unverified_claims):
            return CheckResult(
                name="readme_alignment",
                status=VerificationStatus.WARNING,
                message=f"{len(verified_claims)}/{len(claims)} README claims verified",
                details={
                    "verified_claims": verified_claims,
                    "unverified_claims": unverified_claims,
                },
            )
        else:
            return CheckResult(
                name="readme_alignment",
                status=VerificationStatus.FAILED,
                message=f"Most README claims unverified ({len(unverified_claims)}/{len(claims)})",
                details={
                    "verified_claims": verified_claims,
                    "unverified_claims": unverified_claims,
                },
            )

    def _check_documentation(self, repo_path: Path) -> CheckResult:
        """Check for documentation quality."""
        doc_files = list(repo_path.glob("*.md")) + list(repo_path.glob("docs/**/*.md"))

        readme_exists = (repo_path / "README.md").exists() or (repo_path / "README.rst").exists()

        if not readme_exists:
            return CheckResult(
                name="documentation",
                status=VerificationStatus.FAILED,
                message="No README file found",
            )

        # Check README quality
        readme_path = (
            repo_path / "README.md"
            if (repo_path / "README.md").exists()
            else repo_path / "README.rst"
        )
        try:
            readme_content = readme_path.read_text(encoding="utf-8", errors="ignore")
            readme_lines = len(readme_content.split("\n"))

            if readme_lines < 10:
                return CheckResult(
                    name="documentation",
                    status=VerificationStatus.WARNING,
                    message="README exists but is minimal",
                    details={"doc_files": len(doc_files), "readme_lines": readme_lines},
                )

            has_sections = bool(re.search(r"^#+\s+", readme_content, re.MULTILINE))
            has_code_blocks = "```" in readme_content or "    " in readme_content

            if has_sections and has_code_blocks:
                return CheckResult(
                    name="documentation",
                    status=VerificationStatus.PASSED,
                    message=f"Good documentation ({len(doc_files)} doc files, README with sections and examples)",
                    details={
                        "doc_files": len(doc_files),
                        "readme_lines": readme_lines,
                        "has_sections": has_sections,
                        "has_examples": has_code_blocks,
                    },
                )
            else:
                return CheckResult(
                    name="documentation",
                    status=VerificationStatus.PASSED,
                    message=f"Documentation present ({len(doc_files)} doc files)",
                    details={"doc_files": len(doc_files), "readme_lines": readme_lines},
                )
        except Exception:
            return CheckResult(
                name="documentation",
                status=VerificationStatus.WARNING,
                message="Could not fully analyze documentation",
            )

    def _check_license(self, repo_path: Path) -> CheckResult:
        """Check for license file."""
        license_files = ["LICENSE", "LICENSE.md", "LICENSE.txt", "LICENCE", "COPYING"]

        for lf in license_files:
            if (repo_path / lf).exists():
                try:
                    content = (repo_path / lf).read_text(encoding="utf-8", errors="ignore")
                    # Detect common licenses (check specific licenses first)
                    license_type = "Unknown"
                    if "FSL-1.1-ALv2" in content or "FSL-1.1" in content:
                        license_type = "FSL-1.1-ALv2"
                    elif "FSL" in content:
                        license_type = "FSL"
                    elif "Apache" in content:
                        license_type = "Apache 2.0"
                    elif "GPL" in content:
                        license_type = "GPL"
                    elif "BSD" in content:
                        license_type = "BSD"
                    elif "MIT" in content:
                        license_type = "MIT"

                    return CheckResult(
                        name="license",
                        status=VerificationStatus.PASSED,
                        message=f"License file found ({license_type})",
                        details={"license_type": license_type, "file": lf},
                    )
                except Exception:
                    pass

        return CheckResult(
            name="license",
            status=VerificationStatus.WARNING,
            message="No license file found",
        )

    def _detect_languages(self, repo_path: Path) -> List[str]:
        """Detect programming languages in the repository."""
        extensions = {}

        for file_path in repo_path.rglob("*"):
            if file_path.is_file() and not any(
                part.startswith(".")
                or part in {"node_modules", "venv", "__pycache__", "target", "dist"}
                for part in file_path.parts
            ):
                ext = file_path.suffix
                extensions[ext] = extensions.get(ext, 0) + 1

        language_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".rs": "rust",
            ".go": "go",
            ".java": "java",
            ".rb": "ruby",
        }

        languages = []
        for ext, lang in language_map.items():
            if extensions.get(ext, 0) >= 1:
                languages.append(lang)

        return languages

    def _run_tests(self, repo_path: Path, languages: List[str]) -> Dict[str, Any]:
        """Try to run tests for detected languages."""
        # Use isolated environment if available
        if self._isolated_env and self._isolated_env.language == "python":
            return self._run_tests_in_isolated_env(repo_path)

        for lang in languages:
            if lang not in self.TEST_COMMANDS:
                continue

            for cmd in self.TEST_COMMANDS[lang]:
                try:
                    result = subprocess.run(
                        cmd.split(),
                        cwd=repo_path,
                        capture_output=True,
                        text=True,
                        timeout=self.timeout,
                        env={**os.environ, "CI": "true"},
                    )

                    if result.returncode == 0:
                        return {"success": True, "output": result.stdout}
                    else:
                        error_output = result.stderr or result.stdout
                        # Check if failure is due to missing dependencies
                        dependency_errors = [
                            "ModuleNotFoundError",
                            "ImportError",
                            "No module named",
                            "cannot import name",
                        ]
                        if any(err in error_output for err in dependency_errors):
                            return {
                                "success": False,
                                "dependency_error": True,
                                "error": error_output,
                            }
                        return {
                            "success": False,
                            "error": error_output,
                        }
                except subprocess.TimeoutExpired:
                    return {"success": False, "timeout": True, "error": "Test execution timed out"}
                except FileNotFoundError:
                    continue  # Try next command
                except Exception:
                    continue

        return {"success": True, "skipped": True}  # No test runner found

    def _parse_pytest_summary(self, output: str) -> Dict[str, Any]:
        """Parse pytest output to extract pass/fail counts from summary line."""
        # Look for pytest summary line like: "1126 passed, 5 failed, 2 errors in 300.5s"
        # Or: "===== 1126 passed in 300.5s ====="
        result = {"passed": 0, "failed": 0, "errors": 0, "skipped": 0, "warnings": 0}

        # Search the last 2000 chars where summary appears
        search_text = output[-2000:] if len(output) > 2000 else output

        for key, pattern in [
            ("passed", r"(\d+)\s+passed"),
            ("failed", r"(\d+)\s+failed"),
            ("errors", r"(\d+)\s+error"),
            ("skipped", r"(\d+)\s+skipped"),
            ("warnings", r"(\d+)\s+warning"),
        ]:
            match = re.search(pattern, search_text)
            if match:
                result[key] = int(match.group(1))

        return result

    def _run_tests_in_isolated_env(self, repo_path: Path) -> Dict[str, Any]:
        """Run tests using the isolated virtual environment."""
        if not self._isolated_env:
            return {"success": False, "error": "No isolated environment available"}

        try:
            # Use DependencyInstaller's get_test_command for parallel execution support
            if self._dep_installer:
                cmd = self._dep_installer.get_test_command(
                    self._isolated_env,
                    self._isolated_env.language,
                    parallel=True,  # Enable parallel tests with pytest-xdist
                )
                # Add verbose and short traceback options
                cmd.extend(["-v", "--tb=short"])
            else:
                # Fallback to basic pytest command
                cmd = [str(self._isolated_env.python_path), "-m", "pytest", "-v", "--tb=short"]

            result = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env={**self._isolated_env.activate_env, "CI": "true"},
            )

            full_output = result.stdout + result.stderr

            # Parse pytest summary to get actual pass/fail counts
            summary = self._parse_pytest_summary(full_output)

            # Determine success based on actual test results, not just return code
            # Tests pass if: passed > 0 AND failed == 0 AND errors == 0
            if summary["passed"] > 0 and summary["failed"] == 0 and summary["errors"] == 0:
                return {
                    "success": True,
                    "output": full_output,
                    "summary": summary,
                }

            if result.returncode == 0:
                return {"success": True, "output": full_output, "summary": summary}

            # Check if failure is due to missing dependencies
            dependency_errors = [
                "ModuleNotFoundError",
                "ImportError",
                "No module named",
                "cannot import name",
            ]
            if any(err in full_output for err in dependency_errors):
                return {
                    "success": False,
                    "dependency_error": True,
                    "error": full_output,
                    "summary": summary,
                }

            # Include summary info in the error
            error_msg = full_output
            if summary["passed"] > 0 or summary["failed"] > 0:
                error_msg = f"Tests: {summary['passed']} passed, {summary['failed']} failed, {summary['errors']} errors\n\n{full_output}"

            return {
                "success": False,
                "error": error_msg,
                "summary": summary,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "timeout": True, "error": "Test execution timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _run_linting(self, repo_path: Path, languages: List[str]) -> Dict[str, Any]:
        """Try to run linting for detected languages."""
        # Use isolated environment if available
        if self._isolated_env and self._isolated_env.language == "python":
            return self._run_linting_in_isolated_env(repo_path)

        for lang in languages:
            if lang not in self.LINT_COMMANDS:
                continue

            for cmd in self.LINT_COMMANDS[lang]:
                try:
                    result = subprocess.run(
                        cmd.split(),
                        cwd=repo_path,
                        capture_output=True,
                        text=True,
                        timeout=120,
                    )

                    if result.returncode == 0:
                        return {"success": True, "output": result.stdout}
                    else:
                        # Count actual issue lines (file:line:col: error format)
                        output = result.stdout + result.stderr
                        # Count lines that look like linting errors (path:line:col: code)
                        issue_lines = [
                            line for line in output.split("\n")
                            if line.strip() and ":" in line and not line.startswith(" ")
                        ]
                        issue_count = len(issue_lines)

                        # If no structured issues but command failed, treat as tool error
                        if issue_count == 0 and result.returncode != 0:
                            continue  # Try next linter

                        return {
                            "success": False,
                            "issues": issue_count,
                            "output": output,
                        }
                except FileNotFoundError:
                    continue
                except subprocess.TimeoutExpired:
                    return {"success": False, "error": "Linting timed out"}
                except Exception:
                    continue

        return {"success": True, "skipped": True}

    def _run_linting_in_isolated_env(self, repo_path: Path) -> Dict[str, Any]:
        """Run linting using the isolated virtual environment."""
        if not self._isolated_env:
            return {"success": False, "skipped": True}

        try:
            # Use DependencyInstaller's get_lint_command if available
            if self._dep_installer:
                cmd = self._dep_installer.get_lint_command(
                    self._isolated_env,
                    self._isolated_env.language,
                )
            else:
                # Fallback to basic ruff command
                cmd = [str(self._isolated_env.python_path), "-m", "ruff", "check", "."]
            result = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=120,
                env=self._isolated_env.activate_env,
            )

            if result.returncode == 0:
                return {"success": True, "output": result.stdout}
            else:
                output = result.stdout + result.stderr
                # Count lines that look like linting errors (path:line:col: code)
                issue_lines = [
                    line for line in output.split("\n")
                    if line.strip() and ":" in line and not line.startswith(" ")
                ]
                issue_count = len(issue_lines)

                return {
                    "success": False,
                    "issues": issue_count,
                    "output": output,
                }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Linting timed out"}
        except Exception:
            return {"success": True, "skipped": True}

    def _try_build(self, repo_path: Path, build_systems: List[Dict]) -> Dict[str, Any]:
        """Try to verify build configuration."""
        for build in build_systems:
            lang = build["language"]

            try:
                if lang == "python":
                    # Check if pyproject.toml/setup.py is valid
                    if (repo_path / "pyproject.toml").exists():
                        result = subprocess.run(
                            [
                                "python",
                                "-c",
                                "import tomli; tomli.load(open('pyproject.toml', 'rb'))",
                            ],
                            cwd=repo_path,
                            capture_output=True,
                            timeout=30,
                        )
                        if result.returncode == 0:
                            return {"success": True}

                elif lang == "javascript":
                    # Validate package.json
                    if (repo_path / "package.json").exists():
                        import json

                        with open(repo_path / "package.json") as f:
                            json.load(f)  # Just validate JSON
                        return {"success": True}

                elif lang == "rust":
                    # Check Cargo.toml
                    result = subprocess.run(
                        ["cargo", "check", "--message-format=short"],
                        cwd=repo_path,
                        capture_output=True,
                        timeout=120,
                    )
                    if result.returncode == 0:
                        return {"success": True}

            except FileNotFoundError:
                continue
            except Exception as e:
                return {"success": False, "error": str(e)}

        return {"success": True, "skipped": True}

    def _extract_readme_claims(self, readme_content: str) -> List[Dict[str, str]]:
        """Extract verifiable claims from README."""
        claims = []

        # Look for feature claims
        feature_patterns = [
            r"[-*]\s+(?:Support[s]? for|Provides?|Includes?|Features?:?)\s+(.+)",
            r"[-*]\s+(.+?)\s+support",
            r"(?:can|will|does)\s+(.+)",
        ]

        for pattern in feature_patterns:
            matches = re.findall(pattern, readme_content, re.IGNORECASE)
            for match in matches[:5]:  # Limit
                claims.append({"type": "feature", "claim": match.strip()})

        # Look for language/technology mentions
        tech_pattern = r"(?:written in|built with|uses?|requires?)\s+([A-Z][a-z]+(?:\s+\d+\.?\d*)?)"
        tech_matches = re.findall(tech_pattern, readme_content)
        for match in tech_matches[:3]:
            claims.append({"type": "technology", "claim": match.strip()})

        return claims

    def _verify_claim(self, repo_path: Path, claim: Dict[str, str]) -> bool:
        """Verify a single claim against the codebase."""
        claim_text = claim["claim"].lower()

        # Technology claims - check for files
        tech_indicators = {
            "python": [".py", "requirements.txt", "pyproject.toml"],
            "javascript": [".js", "package.json"],
            "typescript": [".ts", "tsconfig.json"],
            "rust": [".rs", "Cargo.toml"],
            "go": [".go", "go.mod"],
            "react": ["react", "jsx"],
            "vue": [".vue", "vue"],
            "docker": ["Dockerfile", "docker-compose"],
        }

        for tech, indicators in tech_indicators.items():
            if tech in claim_text:
                for indicator in indicators:
                    if list(repo_path.rglob(f"*{indicator}")):
                        return True

        # Generic claim verification - search for keywords in code
        keywords = re.findall(r"\b\w{4,}\b", claim_text)
        for keyword in keywords:
            if keyword in {"with", "that", "this", "from", "into", "have", "been"}:
                continue
            for code_file in repo_path.rglob("*.py"):
                try:
                    if keyword in code_file.read_text(encoding="utf-8", errors="ignore").lower():
                        return True
                except Exception:
                    pass

        return False

    def _calculate_overall(self, checks: List[CheckResult]) -> tuple[VerificationStatus, float]:
        """Calculate overall status and score from individual checks."""
        weights = {
            "tests": 25,
            "security": 25,
            "linting": 15,
            "build": 15,
            "documentation": 10,
            "license": 5,
            "readme_alignment": 5,
        }

        score = 0.0
        has_failure = False
        has_warning = False

        for check in checks:
            weight = weights.get(check.name, 10)

            if check.status == VerificationStatus.PASSED:
                score += weight
            elif check.status == VerificationStatus.WARNING:
                score += weight * 0.5
                has_warning = True
            elif check.status == VerificationStatus.FAILED:
                has_failure = True
            # SKIPPED doesn't affect score

        # Normalize to 0-100
        max_score = sum(
            weights.get(c.name, 10) for c in checks if c.status != VerificationStatus.SKIPPED
        )

        if max_score > 0:
            score = (score / max_score) * 100

        if has_failure:
            overall = VerificationStatus.FAILED
        elif has_warning:
            overall = VerificationStatus.WARNING
        else:
            overall = VerificationStatus.PASSED

        return overall, round(score, 1)
