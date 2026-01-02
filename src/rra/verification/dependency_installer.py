# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Dependency installer for isolated verification.

Creates temporary virtual environments and installs dependencies
to enable running tests and linting without affecting the host system.
"""

import subprocess
import sys
import shutil
import tempfile
import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class IsolatedEnvironment:
    """Represents an isolated virtual environment for verification."""

    venv_path: Path
    python_path: Path
    pip_path: Path
    activate_env: Dict[str, str]
    language: str

    def cleanup(self) -> None:
        """Remove the temporary virtual environment."""
        if self.venv_path.exists():
            shutil.rmtree(self.venv_path, ignore_errors=True)


class DependencyInstaller:
    """
    Manages temporary virtual environments for dependency isolation.

    Creates a temp venv, installs dependencies, and provides paths
    for running verification commands in the isolated environment.
    """

    def __init__(self, timeout: int = 300):
        """
        Initialize the dependency installer.

        Args:
            timeout: Maximum time (seconds) for dependency installation
        """
        self.timeout = timeout
        self._active_envs: list[IsolatedEnvironment] = []

    def create_isolated_env(
        self,
        repo_path: Path,
        language: str = "python",
    ) -> Optional[IsolatedEnvironment]:
        """
        Create an isolated environment and install dependencies.

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
        # Create temp directory for venv
        temp_dir = Path(tempfile.mkdtemp(prefix="rra_verify_"))
        venv_path = temp_dir / "venv"

        try:
            # Create virtual environment
            result = subprocess.run(
                [sys.executable, "-m", "venv", str(venv_path)],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                shutil.rmtree(temp_dir, ignore_errors=True)
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
                shutil.rmtree(temp_dir, ignore_errors=True)
                return None

            env = IsolatedEnvironment(
                venv_path=temp_dir,
                python_path=python_path,
                pip_path=pip_path,
                activate_env=activate_env,
                language="python",
            )
            self._active_envs.append(env)
            return env

        except Exception:
            shutil.rmtree(temp_dir, ignore_errors=True)
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
                result = subprocess.run(
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
                    result = subprocess.run(
                        [str(pip_path), "install", "-e", ".", "-q"],
                        capture_output=True,
                        text=True,
                        timeout=self.timeout,
                        env=env,
                        cwd=repo_path,
                    )

            # Install common testing tools if not already present
            subprocess.run(
                [str(pip_path), "install", "pytest", "pytest-asyncio", "ruff", "-q"],
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
        """Clean up all active environments."""
        for env in self._active_envs:
            env.cleanup()
        self._active_envs.clear()

    def get_test_command(
        self,
        env: IsolatedEnvironment,
        language: str,
    ) -> list[str]:
        """Get the test command for the isolated environment."""
        if language == "python":
            return [str(env.python_path), "-m", "pytest"]
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
