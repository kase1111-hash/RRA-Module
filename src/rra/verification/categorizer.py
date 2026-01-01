# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Code categorization module.

Classifies repositories into categories based on:
- File structure and patterns
- Dependencies
- Code analysis
- README content
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class CodeCategory(str, Enum):
    """Primary categories for code repositories."""
    LIBRARY = "library"  # Reusable code package
    CLI_TOOL = "cli_tool"  # Command-line application
    WEB_APP = "web_app"  # Web application (frontend/backend)
    API_SERVICE = "api_service"  # REST/GraphQL API service
    MOBILE_APP = "mobile_app"  # Mobile application
    DESKTOP_APP = "desktop_app"  # Desktop application
    FRAMEWORK = "framework"  # Development framework
    PLUGIN = "plugin"  # Plugin/extension for another system
    SMART_CONTRACT = "smart_contract"  # Blockchain smart contracts
    DATA_SCIENCE = "data_science"  # Data analysis/ML projects
    DEVOPS = "devops"  # DevOps/infrastructure tools
    DOCUMENTATION = "documentation"  # Documentation projects
    TEMPLATE = "template"  # Project templates/boilerplates
    GAME = "game"  # Game/game engine
    OTHER = "other"  # Uncategorized


class SubCategory(str, Enum):
    """Subcategories for more specific classification."""
    # Library subcategories
    UTILITY = "utility"
    WRAPPER = "wrapper"
    SDK = "sdk"
    PARSER = "parser"

    # Web subcategories
    FRONTEND = "frontend"
    BACKEND = "backend"
    FULLSTACK = "fullstack"
    STATIC_SITE = "static_site"

    # API subcategories
    REST_API = "rest_api"
    GRAPHQL_API = "graphql_api"
    GRPC = "grpc"

    # Smart contract subcategories
    DEFI = "defi"
    NFT = "nft"
    DAO = "dao"
    TOKEN = "token"

    # Data science subcategories
    MACHINE_LEARNING = "machine_learning"
    DATA_ANALYSIS = "data_analysis"
    DATA_PIPELINE = "data_pipeline"
    VISUALIZATION = "visualization"

    # DevOps subcategories
    CI_CD = "ci_cd"
    MONITORING = "monitoring"
    INFRASTRUCTURE = "infrastructure"
    CONTAINER = "container"


@dataclass
class CategoryResult:
    """Result of code categorization."""
    primary_category: CodeCategory
    subcategory: Optional[SubCategory] = None
    confidence: float = 0.0  # 0-1 confidence score
    tags: List[str] = field(default_factory=list)
    technologies: List[str] = field(default_factory=list)
    frameworks: List[str] = field(default_factory=list)
    reasoning: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "primary_category": self.primary_category.value,
            "subcategory": self.subcategory.value if self.subcategory else None,
            "confidence": self.confidence,
            "tags": self.tags,
            "technologies": self.technologies,
            "frameworks": self.frameworks,
            "reasoning": self.reasoning,
        }


class CodeCategorizer:
    """
    Categorizes code repositories based on their structure and content.

    Uses multiple signals to determine the category:
    - File patterns (entry points, config files)
    - Dependencies
    - Code structure
    - README analysis
    """

    # Category indicators based on file patterns
    CATEGORY_PATTERNS = {
        CodeCategory.CLI_TOOL: {
            "files": ["cli.py", "main.py", "__main__.py", "cli/", "bin/"],
            "patterns": [r"argparse", r"click", r"typer", r"fire"],
            "package_json": ["commander", "yargs", "inquirer", "vorpal"],
        },
        CodeCategory.WEB_APP: {
            "files": [
                "app.py", "wsgi.py", "asgi.py", "manage.py",
                "index.html", "app.tsx", "App.vue", "pages/",
                "src/components/", "public/index.html",
            ],
            "patterns": [r"flask", r"django", r"fastapi", r"express", r"next", r"react", r"vue"],
            "package_json": ["react", "vue", "angular", "next", "nuxt", "svelte"],
        },
        CodeCategory.API_SERVICE: {
            "files": ["api/", "routes/", "endpoints/", "handlers/", "swagger.yaml", "openapi.yaml"],
            "patterns": [r"@app\.route", r"@router\.", r"@api\.", r"@get\(", r"@post\("],
            "package_json": ["express", "fastify", "hapi", "koa"],
        },
        CodeCategory.LIBRARY: {
            "files": ["setup.py", "pyproject.toml", "Cargo.toml", "go.mod", "lib/", "src/lib.rs"],
            "patterns": [r"__init__\.py", r"def __init__", r"class \w+:"],
            "package_json_fields": {"main", "module", "exports"},
        },
        CodeCategory.SMART_CONTRACT: {
            "files": ["contracts/", "hardhat.config", "truffle-config", "foundry.toml", "Move.toml"],
            "patterns": [r"pragma solidity", r"contract \w+", r"@openzeppelin"],
            "extensions": [".sol", ".move", ".cairo"],
        },
        CodeCategory.DATA_SCIENCE: {
            "files": ["notebooks/", "*.ipynb", "models/", "data/", "train.py"],
            "patterns": [r"pandas", r"numpy", r"sklearn", r"tensorflow", r"torch", r"keras"],
            "extensions": [".ipynb"],
        },
        CodeCategory.DEVOPS: {
            "files": [
                "Dockerfile", "docker-compose.yml", "kubernetes/", "k8s/",
                "terraform/", ".github/workflows/", "Jenkinsfile",
                "ansible/", "helm/",
            ],
            "patterns": [r"FROM ", r"apiVersion:", r"provider \"aws\""],
        },
        CodeCategory.MOBILE_APP: {
            "files": [
                "android/", "ios/", "App.tsx", "app.json",
                "MainActivity.java", "AppDelegate.swift",
            ],
            "patterns": [r"react-native", r"flutter", r"ionic", r"expo"],
            "package_json": ["react-native", "expo", "@ionic/core"],
        },
        CodeCategory.DESKTOP_APP: {
            "files": ["main.ts", "electron.js", "main.go"],
            "patterns": [r"electron", r"tauri", r"wails", r"fyne"],
            "package_json": ["electron", "@electron-forge"],
        },
        CodeCategory.FRAMEWORK: {
            "files": ["core/", "engine/", "runtime/"],
            "patterns": [r"abstract class", r"interface \w+", r"trait \w+"],
            "indicators": ["extensible", "pluggable", "middleware"],
        },
        CodeCategory.PLUGIN: {
            "files": ["manifest.json", "plugin.json", "extension.json"],
            "patterns": [r"chrome\.runtime", r"browser\.runtime", r"vscode\."],
            "package_json": ["vscode", "@types/chrome"],
        },
        CodeCategory.GAME: {
            "files": ["Assets/", "Scenes/", "game.py", "engine/"],
            "patterns": [r"pygame", r"unity", r"godot", r"phaser", r"pixi"],
            "package_json": ["phaser", "pixi.js", "three"],
        },
        CodeCategory.TEMPLATE: {
            "files": ["cookiecutter.json", "template/", "scaffold/"],
            "patterns": [r"\{\{.*\}\}", r"<%= .* %>"],
            "indicators": ["boilerplate", "starter", "template"],
        },
        CodeCategory.DOCUMENTATION: {
            "files": ["docs/", "mkdocs.yml", "docusaurus.config.js", ".readthedocs.yaml"],
            "patterns": [r"sphinx", r"mkdocs", r"docusaurus"],
            "extensions": [".md", ".rst"],
        },
    }

    # Subcategory indicators
    SUBCATEGORY_PATTERNS = {
        SubCategory.FRONTEND: ["react", "vue", "angular", "svelte", "next", "nuxt"],
        SubCategory.BACKEND: ["fastapi", "django", "flask", "express", "nestjs", "rails"],
        SubCategory.FULLSTACK: ["next", "nuxt", "remix", "sveltekit"],
        SubCategory.REST_API: ["openapi", "swagger", "rest", "routes"],
        SubCategory.GRAPHQL_API: ["graphql", "apollo", "hasura", "prisma"],
        SubCategory.MACHINE_LEARNING: ["tensorflow", "pytorch", "keras", "sklearn", "transformers"],
        SubCategory.DATA_ANALYSIS: ["pandas", "numpy", "matplotlib", "seaborn", "plotly"],
        SubCategory.DEFI: ["uniswap", "aave", "compound", "yield", "swap", "lending"],
        SubCategory.NFT: ["erc721", "erc1155", "nft", "marketplace", "mint"],
        SubCategory.DAO: ["governance", "voting", "proposal", "dao"],
        SubCategory.CI_CD: ["github/workflows", "gitlab-ci", "jenkins", "circle"],
        SubCategory.CONTAINER: ["docker", "kubernetes", "helm", "compose"],
        SubCategory.INFRASTRUCTURE: ["terraform", "pulumi", "cloudformation", "ansible"],
    }

    # Technology detection
    TECHNOLOGY_INDICATORS = {
        "Python": [".py", "requirements.txt", "pyproject.toml"],
        "JavaScript": [".js", "package.json"],
        "TypeScript": [".ts", ".tsx", "tsconfig.json"],
        "Rust": [".rs", "Cargo.toml"],
        "Go": [".go", "go.mod"],
        "Java": [".java", "pom.xml", "build.gradle"],
        "Ruby": [".rb", "Gemfile"],
        "PHP": [".php", "composer.json"],
        "C++": [".cpp", ".hpp", "CMakeLists.txt"],
        "C#": [".cs", ".csproj"],
        "Swift": [".swift", "Package.swift"],
        "Kotlin": [".kt", "build.gradle.kts"],
        "Solidity": [".sol"],
    }

    # Framework detection
    FRAMEWORK_INDICATORS = {
        "FastAPI": ["fastapi", "@app.get", "@app.post"],
        "Django": ["django", "manage.py", "wsgi.py"],
        "Flask": ["flask", "@app.route"],
        "React": ["react", "jsx", "tsx", "useState", "useEffect"],
        "Vue.js": ["vue", ".vue", "v-if", "v-for"],
        "Angular": ["angular", "@Component", "@Injectable"],
        "Next.js": ["next", "getServerSideProps", "getStaticProps"],
        "Express": ["express", "app.get", "app.post", "router."],
        "Spring": ["spring", "@Controller", "@Service"],
        "Rails": ["rails", "ActiveRecord", "ActionController"],
        "Laravel": ["laravel", "Illuminate"],
        "Hardhat": ["hardhat", "ethers"],
        "Foundry": ["foundry", "forge"],
        "PyTorch": ["torch", "nn.Module"],
        "TensorFlow": ["tensorflow", "tf."],
        "Pandas": ["pandas", "DataFrame"],
    }

    def __init__(self):
        """Initialize the code categorizer."""
        pass

    def categorize(
        self,
        repo_path: Path,
        readme_content: Optional[str] = None,
        dependencies: Optional[Dict[str, List[str]]] = None,
    ) -> CategoryResult:
        """
        Categorize a repository based on its structure and content.

        Args:
            repo_path: Path to the repository
            readme_content: Optional README content for analysis
            dependencies: Optional pre-parsed dependencies

        Returns:
            CategoryResult with category and metadata
        """
        scores: Dict[CodeCategory, float] = {cat: 0.0 for cat in CodeCategory}
        tags: Set[str] = set()
        technologies: Set[str] = set()
        frameworks: Set[str] = set()
        reasoning_parts: List[str] = []

        # Analyze file structure
        file_scores, file_techs = self._analyze_files(repo_path)
        for cat, score in file_scores.items():
            scores[cat] += score * 2  # File patterns are strong signals
        technologies.update(file_techs)

        # Analyze dependencies
        if dependencies:
            dep_scores, dep_frameworks = self._analyze_dependencies(dependencies)
            for cat, score in dep_scores.items():
                scores[cat] += score * 1.5
            frameworks.update(dep_frameworks)
        else:
            # Try to extract dependencies
            deps = self._extract_dependencies(repo_path)
            if deps:
                dep_scores, dep_frameworks = self._analyze_dependencies(deps)
                for cat, score in dep_scores.items():
                    scores[cat] += score * 1.5
                frameworks.update(dep_frameworks)

        # Analyze README
        if readme_content:
            readme_scores, readme_tags = self._analyze_readme(readme_content)
            for cat, score in readme_scores.items():
                scores[cat] += score
            tags.update(readme_tags)

        # Analyze code patterns
        code_scores = self._analyze_code_patterns(repo_path)
        for cat, score in code_scores.items():
            scores[cat] += score * 1.5

        # Determine primary category
        max_score = max(scores.values())
        if max_score == 0:
            primary_category = CodeCategory.OTHER
            confidence = 0.3
            reasoning_parts.append("No strong category signals detected")
        else:
            primary_category = max(scores, key=scores.get)
            # Normalize confidence
            total_score = sum(scores.values())
            confidence = min(0.95, scores[primary_category] / total_score if total_score > 0 else 0)

            reasoning_parts.append(f"Detected {primary_category.value} based on file patterns and dependencies")

        # Determine subcategory
        subcategory = self._determine_subcategory(
            primary_category, repo_path, dependencies, frameworks
        )

        # Generate tags
        tags.update(self._generate_tags(primary_category, subcategory, technologies, frameworks))

        return CategoryResult(
            primary_category=primary_category,
            subcategory=subcategory,
            confidence=round(confidence, 2),
            tags=sorted(list(tags)),
            technologies=sorted(list(technologies)),
            frameworks=sorted(list(frameworks)),
            reasoning="; ".join(reasoning_parts),
        )

    def _analyze_files(self, repo_path: Path) -> tuple[Dict[CodeCategory, float], Set[str]]:
        """Analyze file structure for category signals."""
        scores: Dict[CodeCategory, float] = {cat: 0.0 for cat in CodeCategory}
        technologies: Set[str] = set()

        # Get all files (limit for performance)
        try:
            all_files = []
            for f in repo_path.rglob('*'):
                if f.is_file() and not any(
                    part.startswith('.') or part in {'node_modules', 'venv', '__pycache__', 'target', 'dist'}
                    for part in f.parts
                ):
                    all_files.append(f)
                    if len(all_files) > 1000:
                        break
        except Exception as e:
            logger.debug(f"Error scanning repository files: {e}")
            return scores, technologies

        file_names = {f.name for f in all_files}
        file_paths = {str(f.relative_to(repo_path)) for f in all_files}
        extensions = {f.suffix for f in all_files}

        # Check for technology indicators
        for tech, indicators in self.TECHNOLOGY_INDICATORS.items():
            for indicator in indicators:
                if indicator.startswith('.'):
                    if indicator in extensions:
                        technologies.add(tech)
                        break
                elif indicator in file_names:
                    technologies.add(tech)
                    break

        # Check category patterns
        for category, patterns in self.CATEGORY_PATTERNS.items():
            # Check files
            if "files" in patterns:
                for pattern in patterns["files"]:
                    if pattern.endswith('/'):
                        # Directory pattern
                        if any(pattern[:-1] in p for p in file_paths):
                            scores[category] += 1.0
                    elif '*' in pattern:
                        # Wildcard pattern
                        import fnmatch
                        if any(fnmatch.fnmatch(f, pattern) for f in file_names):
                            scores[category] += 0.5
                    else:
                        if pattern in file_names or pattern in file_paths:
                            scores[category] += 1.0

            # Check extensions
            if "extensions" in patterns:
                for ext in patterns["extensions"]:
                    if ext in extensions:
                        scores[category] += 1.5

        return scores, technologies

    def _analyze_dependencies(
        self, dependencies: Dict[str, List[str]]
    ) -> tuple[Dict[CodeCategory, float], Set[str]]:
        """Analyze dependencies for category signals."""
        scores: Dict[CodeCategory, float] = {cat: 0.0 for cat in CodeCategory}
        frameworks: Set[str] = set()

        all_deps = set()
        for deps in dependencies.values():
            all_deps.update(dep.lower().split('[')[0].split('>=')[0].split('==')[0] for dep in deps)

        # Check framework indicators
        for framework, indicators in self.FRAMEWORK_INDICATORS.items():
            for indicator in indicators:
                if indicator.lower() in all_deps:
                    frameworks.add(framework)
                    break

        # Check category patterns from package.json patterns
        for category, patterns in self.CATEGORY_PATTERNS.items():
            if "package_json" in patterns:
                for pkg in patterns["package_json"]:
                    if pkg.lower() in all_deps:
                        scores[category] += 1.0

        # Specific dependency checks
        dep_category_map = {
            "fastapi": CodeCategory.API_SERVICE,
            "flask": CodeCategory.WEB_APP,
            "django": CodeCategory.WEB_APP,
            "express": CodeCategory.API_SERVICE,
            "react": CodeCategory.WEB_APP,
            "vue": CodeCategory.WEB_APP,
            "click": CodeCategory.CLI_TOOL,
            "typer": CodeCategory.CLI_TOOL,
            "argparse": CodeCategory.CLI_TOOL,
            "pandas": CodeCategory.DATA_SCIENCE,
            "tensorflow": CodeCategory.DATA_SCIENCE,
            "torch": CodeCategory.DATA_SCIENCE,
            "web3": CodeCategory.SMART_CONTRACT,
            "ethers": CodeCategory.SMART_CONTRACT,
            "electron": CodeCategory.DESKTOP_APP,
            "tauri": CodeCategory.DESKTOP_APP,
            "react-native": CodeCategory.MOBILE_APP,
            "expo": CodeCategory.MOBILE_APP,
            "pygame": CodeCategory.GAME,
            "mkdocs": CodeCategory.DOCUMENTATION,
            "sphinx": CodeCategory.DOCUMENTATION,
        }

        for dep, category in dep_category_map.items():
            if dep in all_deps:
                scores[category] += 1.5

        return scores, frameworks

    def _analyze_readme(self, readme_content: str) -> tuple[Dict[CodeCategory, float], Set[str]]:
        """Analyze README for category signals."""
        scores: Dict[CodeCategory, float] = {cat: 0.0 for cat in CodeCategory}
        tags: Set[str] = set()
        content_lower = readme_content.lower()

        # Category keywords
        category_keywords = {
            CodeCategory.LIBRARY: ["library", "package", "module", "sdk", "pip install", "npm install"],
            CodeCategory.CLI_TOOL: ["cli", "command line", "command-line", "terminal", "usage:"],
            CodeCategory.WEB_APP: ["web app", "webapp", "website", "dashboard", "frontend"],
            CodeCategory.API_SERVICE: ["api", "endpoint", "rest", "graphql", "server"],
            CodeCategory.SMART_CONTRACT: ["smart contract", "solidity", "blockchain", "ethereum", "defi"],
            CodeCategory.DATA_SCIENCE: ["machine learning", "ml", "data science", "model", "training"],
            CodeCategory.DEVOPS: ["docker", "kubernetes", "deployment", "infrastructure", "ci/cd"],
            CodeCategory.MOBILE_APP: ["mobile", "ios", "android", "app store"],
            CodeCategory.DESKTOP_APP: ["desktop", "windows", "macos", "linux app"],
            CodeCategory.FRAMEWORK: ["framework", "extensible", "plugin system"],
            CodeCategory.PLUGIN: ["plugin", "extension", "addon"],
            CodeCategory.GAME: ["game", "gaming", "player", "score"],
            CodeCategory.TEMPLATE: ["template", "boilerplate", "starter", "scaffold"],
            CodeCategory.DOCUMENTATION: ["documentation", "docs", "wiki", "guide"],
        }

        for category, keywords in category_keywords.items():
            for keyword in keywords:
                if keyword in content_lower:
                    scores[category] += 0.5
                    tags.add(keyword.replace(" ", "-"))

        return scores, tags

    def _analyze_code_patterns(self, repo_path: Path) -> Dict[CodeCategory, float]:
        """Analyze code content for category patterns."""
        scores: Dict[CodeCategory, float] = {cat: 0.0 for cat in CodeCategory}

        # Sample a few code files
        code_extensions = {'.py', '.js', '.ts', '.go', '.rs', '.java', '.sol'}
        sample_files = []

        try:
            for f in repo_path.rglob('*'):
                if f.is_file() and f.suffix in code_extensions and not any(
                    part.startswith('.') or part in {'node_modules', 'venv', '__pycache__'}
                    for part in f.parts
                ):
                    sample_files.append(f)
                    if len(sample_files) >= 20:
                        break
        except Exception as e:
            logger.debug(f"Error collecting sample files: {e}")
            return scores

        for file_path in sample_files:
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')[:5000]

                for category, patterns in self.CATEGORY_PATTERNS.items():
                    if "patterns" in patterns:
                        for pattern in patterns["patterns"]:
                            if re.search(pattern, content, re.IGNORECASE):
                                scores[category] += 0.3
            except (OSError, UnicodeDecodeError) as e:
                logger.debug(f"Could not read {file_path} for pattern analysis: {e}")

        return scores

    def _extract_dependencies(self, repo_path: Path) -> Dict[str, List[str]]:
        """Extract dependencies from common dependency files."""
        deps: Dict[str, List[str]] = {}

        # Python requirements.txt
        req_file = repo_path / "requirements.txt"
        if req_file.exists():
            try:
                with open(req_file) as f:
                    deps["python"] = [
                        line.strip() for line in f
                        if line.strip() and not line.startswith('#')
                    ]
            except (OSError, UnicodeDecodeError) as e:
                logger.debug(f"Could not read requirements.txt: {e}")

        # Node.js package.json
        pkg_file = repo_path / "package.json"
        if pkg_file.exists():
            try:
                import json
                with open(pkg_file) as f:
                    data = json.load(f)
                    deps["javascript"] = list(data.get("dependencies", {}).keys())
                    deps["javascript"].extend(data.get("devDependencies", {}).keys())
            except (OSError, json.JSONDecodeError) as e:
                logger.debug(f"Could not parse package.json: {e}")

        return deps

    def _determine_subcategory(
        self,
        primary_category: CodeCategory,
        repo_path: Path,
        dependencies: Optional[Dict[str, List[str]]],
        frameworks: Set[str],
    ) -> Optional[SubCategory]:
        """Determine subcategory based on primary category and signals."""
        all_deps = set()
        if dependencies:
            for deps in dependencies.values():
                all_deps.update(dep.lower() for dep in deps)

        all_frameworks = {f.lower() for f in frameworks}

        # Map based on primary category
        if primary_category == CodeCategory.WEB_APP:
            if any(f in all_frameworks for f in ["react", "vue.js", "angular"]):
                if any(f in all_frameworks for f in ["next.js", "nuxt.js"]):
                    return SubCategory.FULLSTACK
                return SubCategory.FRONTEND
            if any(f in all_frameworks for f in ["fastapi", "django", "flask", "express"]):
                return SubCategory.BACKEND

        elif primary_category == CodeCategory.API_SERVICE:
            if "graphql" in all_deps or any("graphql" in d for d in all_deps):
                return SubCategory.GRAPHQL_API
            return SubCategory.REST_API

        elif primary_category == CodeCategory.DATA_SCIENCE:
            if any(f in all_frameworks for f in ["pytorch", "tensorflow"]):
                return SubCategory.MACHINE_LEARNING
            if "pandas" in all_frameworks:
                return SubCategory.DATA_ANALYSIS

        elif primary_category == CodeCategory.SMART_CONTRACT:
            # Check for DeFi/NFT/DAO patterns
            try:
                sol_files = list(repo_path.rglob("*.sol"))[:10]
                for sol_file in sol_files:
                    content = sol_file.read_text(encoding='utf-8', errors='ignore').lower()
                    if any(kw in content for kw in ["swap", "liquidity", "lend", "borrow"]):
                        return SubCategory.DEFI
                    if any(kw in content for kw in ["erc721", "erc1155", "nft", "tokenuri"]):
                        return SubCategory.NFT
                    if any(kw in content for kw in ["vote", "proposal", "governance"]):
                        return SubCategory.DAO
            except (OSError, UnicodeDecodeError) as e:
                logger.debug(f"Could not analyze Solidity files for subcategory: {e}")

        elif primary_category == CodeCategory.DEVOPS:
            if (repo_path / ".github" / "workflows").exists():
                return SubCategory.CI_CD
            if (repo_path / "Dockerfile").exists():
                return SubCategory.CONTAINER
            if (repo_path / "terraform").exists():
                return SubCategory.INFRASTRUCTURE

        return None

    def _generate_tags(
        self,
        primary_category: CodeCategory,
        subcategory: Optional[SubCategory],
        technologies: Set[str],
        frameworks: Set[str],
    ) -> Set[str]:
        """Generate tags for the repository."""
        tags = set()

        # Add category as tag
        tags.add(primary_category.value.replace('_', '-'))

        # Add subcategory
        if subcategory:
            tags.add(subcategory.value.replace('_', '-'))

        # Add technologies (lowercase)
        for tech in technologies:
            tags.add(tech.lower())

        # Add frameworks (lowercase)
        for framework in frameworks:
            tags.add(framework.lower().replace('.', '').replace(' ', '-'))

        return tags
