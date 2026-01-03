# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Dependency installer for isolated verification.

Creates virtual environments and installs dependencies
to enable running tests and linting without affecting the host system.

Features:
- Dependency caching based on requirements hash
- Parallel test execution support via pytest-xdist
- Automatic cleanup of temp environments
"""

import subprocess
import sys
import shutil
import tempfile
import hashlib
import os
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass


# Default cache directory
DEFAULT_CACHE_DIR = Path.home() / ".rra_cache" / "venvs"


@dataclass
class IsolatedEnvironment:
    """Represents an isolated virtual environment for verification."""

    venv_path: Path
    python_path: Path
    pip_path: Path
    activate_env: Dict[str, str]
    language: str
    is_cached: bool = False  # Whether this env came from cache

    def cleanup(self) -> None:
        """Remove the virtual environment (only if not cached)."""
        if not self.is_cached and self.venv_path.exists():
            shutil.rmtree(self.venv_path, ignore_errors=True)


class DependencyInstaller:
    """
    Manages virtual environments for dependency isolation.

    Features:
    - Creates cached venvs based on requirements hash
    - Installs dependencies from requirements.txt/pyproject.toml
    - Supports parallel test execution with pytest-xdist
    """

    def __init__(
        self,
        timeout: int = 300,
        use_cache: bool = True,
        cache_dir: Optional[Path] = None,
        parallel_tests: bool = True,
    ):
        """
        Initialize the dependency installer.

        Args:
            timeout: Maximum time (seconds) for dependency installation
            use_cache: Whether to cache and reuse virtual environments
            cache_dir: Directory for cached venvs (default: ~/.rra_cache/venvs)
            parallel_tests: Whether to install pytest-xdist for parallel tests
        """
        self.timeout = timeout
        self.use_cache = use_cache
        self.cache_dir = cache_dir or DEFAULT_CACHE_DIR
        self.parallel_tests = parallel_tests
        self._active_envs: list[IsolatedEnvironment] = []

        # Ensure cache directory exists
        if self.use_cache:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _compute_deps_hash(self, repo_path: Path) -> str:
        """Compute a hash of dependency files to use as cache key."""
        hasher = hashlib.sha256()

        # Hash requirements.txt if exists
        requirements_txt = repo_path / "requirements.txt"
        if requirements_txt.exists():
            hasher.update(requirements_txt.read_bytes())

        # Hash pyproject.toml if exists
        pyproject_toml = repo_path / "pyproject.toml"
        if pyproject_toml.exists():
            hasher.update(pyproject_toml.read_bytes())

        # Include Python version in hash
        hasher.update(f"py{sys.version_info.major}{sys.version_info.minor}".encode())

        return hasher.hexdigest()[:16]

    def _get_cached_env(self, cache_key: str) -> Optional[IsolatedEnvironment]:
        """Get a cached environment if it exists and is valid."""
        if not self.use_cache:
            return None

        cache_path = self.cache_dir / cache_key
        if not cache_path.exists():
            return None

        # Check if the venv is still valid
        if sys.platform == "win32":
            python_path = cache_path / "venv" / "Scripts" / "python.exe"
            pip_path = cache_path / "venv" / "Scripts" / "pip.exe"
        else:
            python_path = cache_path / "venv" / "bin" / "python"
            pip_path = cache_path / "venv" / "bin" / "pip"

        if not python_path.exists():
            # Invalid cache, remove it
            shutil.rmtree(cache_path, ignore_errors=True)
            return None

        # Create environment dict
        activate_env = os.environ.copy()
        activate_env["VIRTUAL_ENV"] = str(cache_path / "venv")
        activate_env["PATH"] = str(python_path.parent) + os.pathsep + activate_env.get("PATH", "")

        env = IsolatedEnvironment(
            venv_path=cache_path,
            python_path=python_path,
            pip_path=pip_path,
            activate_env=activate_env,
            language="python",
            is_cached=True,
        )
        return env

    def create_isolated_env(
        self,
        repo_path: Path,
        language: str = "python",
    ) -> Optional[IsolatedEnvironment]:
        """
        Create an isolated environment and install dependencies.

        Uses caching to avoid reinstalling if dependencies haven't changed.

        Args:
            repo_path: Path to the repository
            language: Primary language (python, javascript, etc.)

        Returns:
            IsolatedEnvironment if successful, None otherwise
        """
        if language == "python":
            return self._create_python_env(repo_path)
        elif language in ("javascript", "typescript"):
            return self._create_node_env(repo_path)
        else:
            return None

    def _create_python_env(self, repo_path: Path) -> Optional[IsolatedEnvironment]:
        """Create a Python virtual environment and install dependencies."""
        # Check cache first
        cache_key = self._compute_deps_hash(repo_path)
        cached_env = self._get_cached_env(cache_key)
        if cached_env:
            self._active_envs.append(cached_env)
            return cached_env

        # Create new environment
        if self.use_cache:
            # Use cache directory
            base_dir = self.cache_dir / cache_key
            base_dir.mkdir(parents=True, exist_ok=True)
        else:
            # Use temp directory
            base_dir = Path(tempfile.mkdtemp(prefix="rra_verify_"))

        venv_path = base_dir / "venv"

        try:
            # Create virtual environment
            result = subprocess.run(
                [sys.executable, "-m", "venv", str(venv_path)],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                shutil.rmtree(base_dir, ignore_errors=True)
                return None

            # Determine paths based on OS
            if sys.platform == "win32":
                python_path = venv_path / "Scripts" / "python.exe"
                pip_path = venv_path / "Scripts" / "pip.exe"
            else:
                python_path = venv_path / "bin" / "python"
                pip_path = venv_path / "bin" / "pip"

            # Create environment dict for subprocess
            activate_env = os.environ.copy()
            activate_env["VIRTUAL_ENV"] = str(venv_path)
            activate_env["PATH"] = str(python_path.parent) + os.pathsep + activate_env.get("PATH", "")

            # Upgrade pip first (silently)
            subprocess.run(
                [str(pip_path), "install", "--upgrade", "pip", "-q"],
                capture_output=True,
                timeout=60,
                env=activate_env,
            )

            # Install dependencies from various sources
            installed = self._install_python_deps(repo_path, pip_path, activate_env)

            if not installed:
                if not self.use_cache:
                    shutil.rmtree(base_dir, ignore_errors=True)
                return None

            env = IsolatedEnvironment(
                venv_path=base_dir,
                python_path=python_path,
                pip_path=pip_path,
                activate_env=activate_env,
                language="python",
                is_cached=self.use_cache,
            )
            self._active_envs.append(env)
            return env

        except Exception:
            if not self.use_cache:
                shutil.rmtree(base_dir, ignore_errors=True)
            return None

    def _install_python_deps(
        self,
        repo_path: Path,
        pip_path: Path,
        env: Dict[str, str],
    ) -> bool:
        """Install Python dependencies from requirements.txt or pyproject.toml."""
        requirements_txt = repo_path / "requirements.txt"
        pyproject_toml = repo_path / "pyproject.toml"

        try:
            # Install from requirements.txt if it exists
            if requirements_txt.exists():
                subprocess.run(
                    [str(pip_path), "install", "-r", str(requirements_txt), "-q"],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    env=env,
                    cwd=repo_path,
                )
                # Continue even if some deps fail - try to install what we can

            # Install from pyproject.toml if it exists (editable install)
            if pyproject_toml.exists():
                # Try editable install with dev dependencies
                result = subprocess.run(
                    [str(pip_path), "install", "-e", ".[dev]", "-q"],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    env=env,
                    cwd=repo_path,
                )
                # If [dev] extras fail, try without
                if result.returncode != 0:
                    subprocess.run(
                        [str(pip_path), "install", "-e", ".", "-q"],
                        capture_output=True,
                        text=True,
                        timeout=self.timeout,
                        env=env,
                        cwd=repo_path,
                    )

            # Install testing tools
            test_tools = ["pytest", "pytest-asyncio", "ruff"]
            if self.parallel_tests:
                test_tools.append("pytest-xdist")  # For parallel test execution

            subprocess.run(
                [str(pip_path), "install"] + test_tools + ["-q"],
                capture_output=True,
                timeout=120,
                env=env,
            )

            return True

        except subprocess.TimeoutExpired:
            return False
        except Exception:
            return False

    def _create_node_env(self, repo_path: Path) -> Optional[IsolatedEnvironment]:
        """Create a Node.js environment with dependencies installed."""
        package_json = repo_path / "package.json"

        if not package_json.exists():
            return None

        try:
            # Check if npm is available
            result = subprocess.run(
                ["npm", "--version"],
                capture_output=True,
                timeout=10,
            )
            if result.returncode != 0:
                return None

            # Install dependencies in repo (npm uses node_modules in place)
            result = subprocess.run(
                ["npm", "install", "--silent"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )

            if result.returncode != 0:
                return None

            # Create a pseudo-environment for Node
            env = IsolatedEnvironment(
                venv_path=repo_path / "node_modules",
                python_path=Path("node"),  # Not used for JS
                pip_path=Path("npm"),  # Not used for JS
                activate_env=os.environ.copy(),
                language="javascript",
            )
            self._active_envs.append(env)
            return env

        except Exception:
            return None

    def cleanup_all(self) -> None:
        """Clean up all non-cached environments."""
        for env in self._active_envs:
            if not env.is_cached:
                env.cleanup()
        self._active_envs.clear()

    def clear_cache(self) -> None:
        """Clear all cached virtual environments."""
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir, ignore_errors=True)
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_cache_size(self) -> int:
        """Get total size of cached environments in bytes."""
        if not self.cache_dir.exists():
            return 0

        total = 0
        for path in self.cache_dir.rglob("*"):
            if path.is_file():
                total += path.stat().st_size
        return total

    def get_test_command(
        self,
        env: IsolatedEnvironment,
        language: str,
        parallel: bool = True,
    ) -> list[str]:
        """
        Get the test command for the isolated environment.

        Args:
            env: The isolated environment
            language: Programming language
            parallel: Whether to run tests in parallel (uses pytest-xdist)

        Returns:
            Command list to execute
        """
        if language == "python":
            cmd = [str(env.python_path), "-m", "pytest"]
            if parallel and self.parallel_tests:
                # Use all available CPU cores
                cmd.extend(["-n", "auto"])
            return cmd
        elif language in ("javascript", "typescript"):
            return ["npm", "test"]
        else:
            return []

    def get_lint_command(
        self,
        env: IsolatedEnvironment,
        language: str,
    ) -> list[str]:
        """Get the lint command for the isolated environment."""
        if language == "python":
            return [str(env.python_path), "-m", "ruff", "check", "."]
        elif language in ("javascript", "typescript"):
            return ["npm", "run", "lint"]
        else:
            return []
