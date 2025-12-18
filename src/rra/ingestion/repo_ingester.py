"""
Repository ingestion and parsing module.

Handles cloning, parsing, and extracting key information from repositories
to build the Agent Knowledge Base (AKB).
"""

import os
import re
import json
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime
import git
from git.exc import GitCommandError

from rra.config.market_config import MarketConfig
from rra.ingestion.knowledge_base import KnowledgeBase


class RepoIngester:
    """
    Handles repository ingestion and knowledge base generation.

    This class manages the process of cloning repositories, parsing their
    contents, and generating structured knowledge bases for agent reasoning.
    """

    def __init__(self, workspace_dir: Path = Path("./cloned_repos")):
        """
        Initialize the RepoIngester.

        Args:
            workspace_dir: Directory where repositories will be cloned
        """
        self.workspace_dir = workspace_dir
        self.workspace_dir.mkdir(parents=True, exist_ok=True)

    def ingest(
        self,
        repo_url: str,
        force_refresh: bool = False
    ) -> KnowledgeBase:
        """
        Ingest a repository and generate its knowledge base.

        Args:
            repo_url: URL of the GitHub repository
            force_refresh: If True, re-clone even if repo exists locally

        Returns:
            KnowledgeBase instance containing parsed repository information

        Raises:
            ValueError: If repo_url is invalid
            GitCommandError: If cloning fails
        """
        repo_name = self._extract_repo_name(repo_url)
        repo_path = self.workspace_dir / repo_name

        # Clone or update repository
        if force_refresh and repo_path.exists():
            import shutil
            shutil.rmtree(repo_path)

        if not repo_path.exists():
            print(f"Cloning repository: {repo_url}")
            git.Repo.clone_from(repo_url, repo_path)
        else:
            print(f"Repository already exists, pulling latest changes")
            repo = git.Repo(repo_path)
            repo.remotes.origin.pull()

        # Parse repository contents
        print(f"Parsing repository: {repo_name}")
        kb = self._parse_repository(repo_path, repo_url)

        return kb

    def update_knowledge_base(self, repo_path: Path) -> KnowledgeBase:
        """
        Update the knowledge base for an existing repository.

        Args:
            repo_path: Path to the local repository

        Returns:
            Updated KnowledgeBase instance
        """
        if not repo_path.exists():
            raise FileNotFoundError(f"Repository not found: {repo_path}")

        # Pull latest changes
        repo = git.Repo(repo_path)
        repo.remotes.origin.pull()

        # Re-parse repository
        repo_url = repo.remotes.origin.url
        return self._parse_repository(repo_path, repo_url)

    def _extract_repo_name(self, repo_url: str) -> str:
        """
        Extract repository name from URL.

        Args:
            repo_url: Repository URL

        Returns:
            Repository name (owner_reponame format)
        """
        # Remove .git suffix and extract owner/repo
        match = re.search(r'github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?$', repo_url)
        if not match:
            raise ValueError(f"Invalid GitHub repository URL: {repo_url}")

        owner, repo = match.groups()
        return f"{owner}_{repo}"

    def _parse_repository(self, repo_path: Path, repo_url: str) -> KnowledgeBase:
        """
        Parse repository contents and generate knowledge base.

        Args:
            repo_path: Path to the local repository
            repo_url: Original repository URL

        Returns:
            KnowledgeBase instance
        """
        kb = KnowledgeBase(repo_path=repo_path, repo_url=repo_url)

        # Parse market configuration if exists
        market_config_path = repo_path / ".market.yaml"
        if market_config_path.exists():
            kb.market_config = MarketConfig.from_yaml(market_config_path)

        # Extract repository metadata
        kb.metadata = self._extract_metadata(repo_path)

        # Parse code structure
        kb.code_structure = self._parse_code_structure(repo_path)

        # Extract dependencies
        kb.dependencies = self._extract_dependencies(repo_path)

        # Parse README and documentation
        kb.documentation = self._parse_documentation(repo_path)

        # Extract API endpoints if present
        kb.api_endpoints = self._extract_api_endpoints(repo_path)

        # Parse test suites
        kb.tests = self._parse_tests(repo_path)

        # Calculate repository statistics
        kb.statistics = self._calculate_statistics(repo_path)

        return kb

    def _extract_metadata(self, repo_path: Path) -> Dict[str, Any]:
        """Extract repository metadata from git."""
        try:
            repo = git.Repo(repo_path)

            # Get latest commit info
            latest_commit = repo.head.commit

            metadata = {
                "last_commit_sha": latest_commit.hexsha,
                "last_commit_date": datetime.fromtimestamp(latest_commit.committed_date).isoformat(),
                "last_commit_message": latest_commit.message.strip(),
                "author": str(latest_commit.author),
                "branch": repo.active_branch.name,
                "remote_url": repo.remotes.origin.url if repo.remotes else None,
            }

            # Count total commits
            metadata["total_commits"] = sum(1 for _ in repo.iter_commits())

            return metadata
        except Exception as e:
            print(f"Warning: Could not extract git metadata: {e}")
            return {}

    def _parse_code_structure(self, repo_path: Path) -> Dict[str, List[str]]:
        """
        Parse code structure to identify key files and modules.

        Returns a dictionary mapping file extensions to file paths.
        """
        structure = {}
        ignore_dirs = {'.git', '__pycache__', 'node_modules', 'venv', 'env', '.venv', 'dist', 'build'}

        for file_path in repo_path.rglob('*'):
            if file_path.is_file():
                # Skip files in ignored directories
                if any(ignored in file_path.parts for ignored in ignore_dirs):
                    continue

                ext = file_path.suffix
                if ext:
                    rel_path = file_path.relative_to(repo_path)
                    structure.setdefault(ext, []).append(str(rel_path))

        return structure

    def _extract_dependencies(self, repo_path: Path) -> Dict[str, List[str]]:
        """
        Extract dependencies from various package files.

        Supports: requirements.txt, package.json, Cargo.toml, go.mod, etc.
        """
        dependencies = {}

        # Python: requirements.txt
        req_file = repo_path / "requirements.txt"
        if req_file.exists():
            with open(req_file) as f:
                dependencies["python"] = [
                    line.strip() for line in f
                    if line.strip() and not line.startswith('#')
                ]

        # Python: pyproject.toml
        pyproject = repo_path / "pyproject.toml"
        if pyproject.exists():
            try:
                import tomli
                with open(pyproject, 'rb') as f:
                    data = tomli.load(f)
                    if "project" in data and "dependencies" in data["project"]:
                        dependencies.setdefault("python", []).extend(
                            data["project"]["dependencies"]
                        )
            except:
                pass

        # JavaScript/Node: package.json
        package_json = repo_path / "package.json"
        if package_json.exists():
            try:
                with open(package_json) as f:
                    data = json.load(f)
                    deps = list(data.get("dependencies", {}).keys())
                    dev_deps = list(data.get("devDependencies", {}).keys())
                    dependencies["javascript"] = deps + dev_deps
            except:
                pass

        # Rust: Cargo.toml
        cargo_toml = repo_path / "Cargo.toml"
        if cargo_toml.exists():
            try:
                import tomli
                with open(cargo_toml, 'rb') as f:
                    data = tomli.load(f)
                    if "dependencies" in data:
                        dependencies["rust"] = list(data["dependencies"].keys())
            except:
                pass

        return dependencies

    def _parse_documentation(self, repo_path: Path) -> Dict[str, str]:
        """Parse README and other documentation files."""
        docs = {}

        # Common documentation files
        doc_files = ["README.md", "README.rst", "README.txt", "CHANGELOG.md", "CONTRIBUTING.md"]

        for doc_file in doc_files:
            file_path = repo_path / doc_file
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        docs[doc_file] = f.read()
                except Exception as e:
                    print(f"Warning: Could not read {doc_file}: {e}")

        return docs

    def _extract_api_endpoints(self, repo_path: Path) -> List[Dict[str, Any]]:
        """
        Extract API endpoints from common web frameworks.

        This is a simplified implementation - in production would use
        AST parsing for more accurate detection.
        """
        endpoints = []

        # Patterns for common frameworks
        patterns = {
            'flask': r'@app\.route\(["\']([^"\']+)["\']',
            'fastapi': r'@app\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']',
            'express': r'app\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']',
        }

        for py_file in repo_path.rglob('*.py'):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                    for framework, pattern in patterns.items():
                        matches = re.finditer(pattern, content)
                        for match in matches:
                            endpoints.append({
                                'file': str(py_file.relative_to(repo_path)),
                                'framework': framework,
                                'path': match.group(1) if 'flask' in framework else match.group(2),
                                'method': match.group(1) if framework != 'flask' else 'GET'
                            })
            except:
                pass

        return endpoints

    def _parse_tests(self, repo_path: Path) -> Dict[str, int]:
        """
        Count and categorize test files.

        Returns statistics about test coverage.
        """
        test_stats = {
            'test_files': 0,
            'test_functions': 0,
        }

        test_patterns = ['test_*.py', '*_test.py', 'test*.js', '*.test.js', '*.spec.js']

        for pattern in test_patterns:
            for test_file in repo_path.rglob(pattern):
                test_stats['test_files'] += 1

                try:
                    with open(test_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                        # Count test functions (simplified)
                        test_stats['test_functions'] += len(
                            re.findall(r'def test_|test\(|it\(', content)
                        )
                except:
                    pass

        return test_stats

    def _calculate_statistics(self, repo_path: Path) -> Dict[str, Any]:
        """Calculate repository statistics."""
        stats = {
            'total_files': 0,
            'total_lines': 0,
            'code_files': 0,
            'languages': set(),
        }

        # Language detection based on extensions
        language_map = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.ts': 'TypeScript',
            '.rs': 'Rust',
            '.go': 'Go',
            '.java': 'Java',
            '.cpp': 'C++',
            '.c': 'C',
            '.rb': 'Ruby',
            '.php': 'PHP',
        }

        ignore_dirs = {'.git', '__pycache__', 'node_modules', 'venv', 'env', '.venv', 'dist', 'build'}

        for file_path in repo_path.rglob('*'):
            if file_path.is_file():
                # Skip ignored directories
                if any(ignored in file_path.parts for ignored in ignore_dirs):
                    continue

                stats['total_files'] += 1

                ext = file_path.suffix
                if ext in language_map:
                    stats['code_files'] += 1
                    stats['languages'].add(language_map[ext])

                    # Count lines
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            stats['total_lines'] += sum(1 for _ in f)
                    except:
                        pass

        stats['languages'] = list(stats['languages'])
        return stats
