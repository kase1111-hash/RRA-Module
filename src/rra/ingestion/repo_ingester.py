# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Repository ingestion and parsing module.

Handles cloning, parsing, and extracting key information from repositories
to build the Agent Knowledge Base (AKB).

Now includes:
- Code verification (tests, linting, security)
- README parsing and metadata extraction
- Automatic categorization
- Blockchain purchase link generation
"""

import re
import json
import logging
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime
from urllib.parse import urlparse
import git

logger = logging.getLogger(__name__)

from rra.config.market_config import MarketConfig
from rra.ingestion.knowledge_base import KnowledgeBase
from rra.exceptions import ValidationError
from rra.status.dreaming import get_dreaming_status


# Security constants
MAX_FILES = 10000  # Maximum files to process per repository
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB max file size
MAX_COMMITS_TO_COUNT = 10000  # Maximum commits to count
ALLOWED_GIT_HOSTS = ["github.com", "gitlab.com", "bitbucket.org"]


class RepoIngester:
    """
    Handles repository ingestion and knowledge base generation.

    This class manages the process of cloning repositories, parsing their
    contents, and generating structured knowledge bases for agent reasoning.

    Now includes verification, categorization, and blockchain link generation.
    """

    def __init__(
        self,
        workspace_dir: Path = Path("./cloned_repos"),
        verify_code: bool = True,
        categorize: bool = True,
        generate_blockchain_links: bool = True,
        owner_address: Optional[str] = None,
        network: str = "testnet",
        test_timeout: int = 300,
        auto_install_deps: bool = False,
        use_cache: bool = True,
    ):
        """
        Initialize the RepoIngester.

        Args:
            workspace_dir: Directory where repositories will be cloned
            verify_code: Whether to run code verification
            categorize: Whether to categorize the repository
            generate_blockchain_links: Whether to generate blockchain links
            owner_address: Ethereum address for blockchain registration
            network: Blockchain network ("mainnet", "testnet", "localhost")
            test_timeout: Timeout in seconds for test execution
            auto_install_deps: Automatically install dependencies in temp environment
            use_cache: Whether to cache virtual environments for faster subsequent runs
        """
        self.workspace_dir = workspace_dir
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.verify_code = verify_code
        self.categorize = categorize
        self.generate_blockchain_links = generate_blockchain_links
        self.owner_address = owner_address
        self.network = network
        self.test_timeout = test_timeout
        self.auto_install_deps = auto_install_deps
        self.use_cache = use_cache

        # Initialize verification and categorization modules
        self._verifier = None
        self._categorizer = None
        self._readme_parser = None
        self._link_generator = None

    @property
    def verifier(self):
        """Lazy-load the code verifier."""
        if self._verifier is None:
            from rra.verification.verifier import CodeVerifier

            self._verifier = CodeVerifier(
                timeout=self.test_timeout,
                auto_install_deps=self.auto_install_deps,
                use_cache=self.use_cache,
            )
        return self._verifier

    @property
    def categorizer(self):
        """Lazy-load the code categorizer."""
        if self._categorizer is None:
            from rra.verification.categorizer import CodeCategorizer

            self._categorizer = CodeCategorizer()
        return self._categorizer

    @property
    def readme_parser(self):
        """Lazy-load the README parser."""
        if self._readme_parser is None:
            from rra.verification.readme_parser import ReadmeParser

            self._readme_parser = ReadmeParser()
        return self._readme_parser

    @property
    def link_generator(self):
        """Lazy-load the blockchain link generator."""
        if self._link_generator is None:
            from rra.verification.blockchain_link import BlockchainLinkGenerator, NetworkType

            network_type = NetworkType(self.network)
            self._link_generator = BlockchainLinkGenerator(network=network_type)
        return self._link_generator

    def _validate_repo_url(self, repo_url: str) -> None:
        """
        Validate repository URL to prevent command injection and SSRF.

        Args:
            repo_url: URL to validate

        Raises:
            ValueError: If URL is invalid or potentially malicious
        """
        if not repo_url:
            raise ValidationError(
                message="Repository URL cannot be empty",
                field="repo_url",
                constraint="must not be empty",
            )

        # Only allow HTTPS protocol
        parsed = urlparse(repo_url)
        if parsed.scheme != "https":
            raise ValidationError(
                message="Only HTTPS GitHub URLs are allowed",
                field="repo_url",
                value=parsed.scheme,
                constraint="scheme must be 'https'",
            )

        # Check for allowed hosts
        hostname = parsed.hostname
        if not hostname:
            raise ValidationError(
                message="Invalid URL: no hostname",
                field="repo_url",
                value=repo_url,
                constraint="must have valid hostname",
            )

        if not any(hostname.endswith(host) for host in ALLOWED_GIT_HOSTS):
            raise ValidationError(
                message=f"Only allowed git hosts are permitted. Got: {hostname}",
                field="repo_url",
                value=hostname,
                constraint=f"must be one of {ALLOWED_GIT_HOSTS}",
            )

        # Validate path format to prevent command injection
        # Path should be /owner/repo or /owner/repo.git
        path = parsed.path.rstrip("/")
        if not re.match(r"^/[\w\-\.]+/[\w\-\.]+(?:\.git)?$", path):
            raise ValidationError(
                message=f"Invalid repository path format: {path}",
                field="repo_url",
                value=path,
                constraint="must match /owner/repo format",
            )

        # Reject URLs with query strings or fragments (potential injection)
        if parsed.query or parsed.fragment:
            raise ValidationError(
                message="Repository URL cannot contain query strings or fragments",
                field="repo_url",
                value=repo_url,
                constraint="must not have query or fragment",
            )

    def ingest(self, repo_url: str, force_refresh: bool = False) -> KnowledgeBase:
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
        dreaming = get_dreaming_status()

        # Security: Validate URL before any git operations
        dreaming.start("Validating repository URL")
        self._validate_repo_url(repo_url)
        dreaming.complete("Validating repository URL")

        repo_name = self._extract_repo_name(repo_url)
        repo_path = self.workspace_dir / repo_name

        # Clone or update repository
        if force_refresh and repo_path.exists():
            import shutil

            shutil.rmtree(repo_path)

        if not repo_path.exists():
            dreaming.start("Cloning repository")
            print(f"Cloning repository: {repo_url}")
            git.Repo.clone_from(repo_url, repo_path)
            dreaming.complete("Cloning repository")
        else:
            dreaming.start("Pulling latest changes")
            print("Repository already exists, pulling latest changes")
            repo = git.Repo(repo_path)
            repo.remotes.origin.pull()
            dreaming.complete("Pulling latest changes")

        # Parse repository contents
        dreaming.start("Parsing repository")
        print(f"Parsing repository: {repo_name}")
        kb = self._parse_repository(repo_path, repo_url)
        dreaming.complete("Parsing repository")

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
        match = re.search(r"github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?$", repo_url)
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
        dreaming = get_dreaming_status()
        kb = KnowledgeBase(repo_path=repo_path, repo_url=repo_url)

        # Parse market configuration if exists
        market_config_path = repo_path / ".market.yaml"
        if market_config_path.exists():
            kb.market_config = MarketConfig.from_yaml(market_config_path)

        # Extract repository metadata
        dreaming.start("Extracting git metadata")
        kb.metadata = self._extract_metadata(repo_path)
        dreaming.complete("Extracting git metadata")

        # Parse code structure
        dreaming.start("Analyzing code structure")
        kb.code_structure = self._parse_code_structure(repo_path)
        dreaming.complete("Analyzing code structure")

        # Extract dependencies
        dreaming.start("Extracting dependencies")
        kb.dependencies = self._extract_dependencies(repo_path)
        dreaming.complete("Extracting dependencies")

        # Parse README and documentation
        dreaming.start("Parsing documentation")
        kb.documentation = self._parse_documentation(repo_path)
        dreaming.complete("Parsing documentation")

        # Extract API endpoints if present
        dreaming.start("Extracting API endpoints")
        kb.api_endpoints = self._extract_api_endpoints(repo_path)
        dreaming.complete("Extracting API endpoints")

        # Parse test suites
        dreaming.start("Analyzing test suites")
        kb.tests = self._parse_tests(repo_path)
        dreaming.complete("Analyzing test suites")

        # Calculate repository statistics
        dreaming.start("Calculating statistics")
        kb.statistics = self._calculate_statistics(repo_path)
        dreaming.complete("Calculating statistics")

        # Parse README metadata
        readme_content = kb.documentation.get("README.md", "")
        if readme_content:
            dreaming.start("Parsing README metadata")
            print("  Parsing README metadata...")
            readme_meta = self.readme_parser.parse_from_content(readme_content)
            kb.readme_metadata = readme_meta.to_dict()
            dreaming.complete("Parsing README metadata")

        # Verify code
        if self.verify_code:
            dreaming.start("Verifying code quality")
            print("  Verifying code...")
            verification_result = self.verifier.verify(
                repo_path=repo_path,
                repo_url=repo_url,
                readme_content=readme_content,
            )
            kb.verification = verification_result.to_dict()
            print(f"    Verification score: {verification_result.score}/100")
            dreaming.complete("Verifying code quality")

        # Categorize repository
        if self.categorize:
            dreaming.start("Categorizing repository")
            print("  Categorizing repository...")
            category_result = self.categorizer.categorize(
                repo_path=repo_path,
                readme_content=readme_content,
                dependencies=kb.dependencies,
            )
            kb.category = category_result.to_dict()
            print(f"    Category: {category_result.primary_category.value}")
            dreaming.complete("Categorizing repository")

        # Generate blockchain links
        if self.generate_blockchain_links and self.owner_address:
            dreaming.start("Generating blockchain links")
            print("  Generating blockchain links...")
            kb.blockchain_links = self._generate_blockchain_links(kb)
            print(
                f"    Generated {len(kb.blockchain_links.get('purchase_links', []))} purchase links"
            )
            dreaming.complete("Generating blockchain links")

        return kb

    def _generate_blockchain_links(self, kb: KnowledgeBase) -> Dict[str, Any]:
        """
        Generate blockchain purchase links for the repository.

        Args:
            kb: KnowledgeBase with parsed repository information

        Returns:
            Dictionary with blockchain link information
        """
        # Get pricing from market config or use defaults
        pricing = {
            "standard": 0.05,
            "premium": 0.15,
            "enterprise": 0.50,
        }

        if kb.market_config:
            try:
                # Parse prices from market config
                target = float(kb.market_config.target_price.replace(" ETH", "").replace("ETH", ""))
                floor = float(kb.market_config.floor_price.replace(" ETH", "").replace("ETH", ""))
                pricing = {
                    "standard": floor,
                    "premium": target,
                    "enterprise": target * 3,
                }
            except (ValueError, AttributeError):
                pass

        # Get description
        description = ""
        if kb.readme_metadata:
            description = kb.readme_metadata.get("short_description", "")
        if not description and kb.documentation.get("README.md"):
            description = kb.documentation["README.md"][:200]

        # Get category
        category = "other"
        if kb.category:
            category = kb.category.get("primary_category", "other")

        # Get verification score
        verification_score = 0.0
        if kb.verification:
            verification_score = kb.verification.get("score", 0.0)

        # Get tags and technologies
        tags = []
        technologies = []
        if kb.category:
            tags = kb.category.get("tags", [])
            technologies = kb.category.get("technologies", [])

        # Generate marketplace listing
        listing = self.link_generator.generate_marketplace_listing(
            repo_url=kb.repo_url,
            repo_name=kb.repo_url.split("/")[-1].replace(".git", ""),
            description=description,
            category=category,
            owner_address=self.owner_address,
            pricing=pricing,
            verification_score=verification_score,
            tags=tags,
            technologies=technologies,
        )

        return listing.to_dict()

    def _extract_metadata(self, repo_path: Path) -> Dict[str, Any]:
        """Extract repository metadata from git."""
        try:
            repo = git.Repo(repo_path)

            # Get latest commit info
            latest_commit = repo.head.commit

            metadata = {
                "last_commit_sha": latest_commit.hexsha,
                "last_commit_date": datetime.fromtimestamp(
                    latest_commit.committed_date
                ).isoformat(),
                "last_commit_message": latest_commit.message.strip(),
                "author": str(latest_commit.author),
                "branch": repo.active_branch.name,
                "remote_url": repo.remotes.origin.url if repo.remotes else None,
            }

            # Count total commits
            metadata["total_commits"] = sum(1 for _ in repo.iter_commits())

            return metadata
        except Exception as e:
            logger.warning(f"Could not extract git metadata: {e}")
            return {}

    def _parse_code_structure(self, repo_path: Path) -> Dict[str, List[str]]:
        """
        Parse code structure to identify key files and modules.

        Returns a dictionary mapping file extensions to file paths.
        """
        structure = {}
        ignore_dirs = {
            ".git",
            "__pycache__",
            "node_modules",
            "venv",
            "env",
            ".venv",
            "dist",
            "build",
        }

        for file_path in repo_path.rglob("*"):
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
                    line.strip() for line in f if line.strip() and not line.startswith("#")
                ]

        # Python: pyproject.toml
        pyproject = repo_path / "pyproject.toml"
        if pyproject.exists():
            try:
                import tomli

                with open(pyproject, "rb") as f:
                    data = tomli.load(f)
                    if "project" in data and "dependencies" in data["project"]:
                        dependencies.setdefault("python", []).extend(
                            data["project"]["dependencies"]
                        )
            except ImportError:
                logger.debug("tomli not installed, skipping pyproject.toml parsing")
            except (OSError, IOError) as e:
                logger.warning(f"Could not read pyproject.toml: {e}")
            except Exception as e:
                logger.warning(f"Could not parse pyproject.toml: {e}")

        # JavaScript/Node: package.json
        package_json = repo_path / "package.json"
        if package_json.exists():
            try:
                with open(package_json) as f:
                    data = json.load(f)
                    deps = list(data.get("dependencies", {}).keys())
                    dev_deps = list(data.get("devDependencies", {}).keys())
                    dependencies["javascript"] = deps + dev_deps
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON in package.json: {e}")
            except (OSError, IOError) as e:
                logger.warning(f"Could not read package.json: {e}")

        # Rust: Cargo.toml
        cargo_toml = repo_path / "Cargo.toml"
        if cargo_toml.exists():
            try:
                import tomli

                with open(cargo_toml, "rb") as f:
                    data = tomli.load(f)
                    if "dependencies" in data:
                        dependencies["rust"] = list(data["dependencies"].keys())
            except ImportError:
                logger.debug("tomli not installed, skipping Cargo.toml parsing")
            except (OSError, IOError) as e:
                logger.warning(f"Could not read Cargo.toml: {e}")
            except Exception as e:
                logger.warning(f"Could not parse Cargo.toml: {e}")

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
                    with open(file_path, "r", encoding="utf-8") as f:
                        docs[doc_file] = f.read()
                except Exception as e:
                    logger.warning(f"Could not read {doc_file}: {e}")

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
            "flask": r'@app\.route\(["\']([^"\']+)["\']',
            "fastapi": r'@app\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']',
            "express": r'app\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']',
        }

        for py_file in repo_path.rglob("*.py"):
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()

                    for framework, pattern in patterns.items():
                        matches = re.finditer(pattern, content)
                        for match in matches:
                            endpoints.append(
                                {
                                    "file": str(py_file.relative_to(repo_path)),
                                    "framework": framework,
                                    "path": (
                                        match.group(1) if "flask" in framework else match.group(2)
                                    ),
                                    "method": match.group(1) if framework != "flask" else "GET",
                                }
                            )
            except (OSError, IOError, UnicodeDecodeError) as e:
                logger.debug(f"Could not read {py_file}: {e}")

        return endpoints

    def _parse_tests(self, repo_path: Path) -> Dict[str, int]:
        """
        Count and categorize test files.

        Returns statistics about test coverage.
        """
        test_stats = {
            "test_files": 0,
            "test_functions": 0,
        }

        test_patterns = ["test_*.py", "*_test.py", "test*.js", "*.test.js", "*.spec.js"]

        for pattern in test_patterns:
            for test_file in repo_path.rglob(pattern):
                test_stats["test_files"] += 1

                try:
                    with open(test_file, "r", encoding="utf-8") as f:
                        content = f.read()

                        # Count test functions (simplified)
                        test_stats["test_functions"] += len(
                            re.findall(r"def test_|test\(|it\(", content)
                        )
                except (OSError, IOError, UnicodeDecodeError) as e:
                    logger.debug(f"Could not read test file {test_file}: {e}")

        return test_stats

    def _calculate_statistics(self, repo_path: Path) -> Dict[str, Any]:
        """Calculate repository statistics."""
        stats = {
            "total_files": 0,
            "total_lines": 0,
            "code_files": 0,
            "languages": set(),
        }

        # Language detection based on extensions
        language_map = {
            ".py": "Python",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".rs": "Rust",
            ".go": "Go",
            ".java": "Java",
            ".cpp": "C++",
            ".c": "C",
            ".rb": "Ruby",
            ".php": "PHP",
        }

        ignore_dirs = {
            ".git",
            "__pycache__",
            "node_modules",
            "venv",
            "env",
            ".venv",
            "dist",
            "build",
        }

        for file_path in repo_path.rglob("*"):
            if file_path.is_file():
                # Skip ignored directories
                if any(ignored in file_path.parts for ignored in ignore_dirs):
                    continue

                stats["total_files"] += 1

                ext = file_path.suffix
                if ext in language_map:
                    stats["code_files"] += 1
                    stats["languages"].add(language_map[ext])

                    # Count lines
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            stats["total_lines"] += sum(1 for _ in f)
                    except (OSError, IOError, UnicodeDecodeError) as e:
                        logger.debug(f"Could not count lines in {file_path}: {e}")

        stats["languages"] = list(stats["languages"])
        return stats
