# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Tests for the verification module.

Tests code verification, README parsing, categorization, and blockchain link generation.
"""

from pathlib import Path
from tempfile import TemporaryDirectory


class TestCodeVerifier:
    """Tests for CodeVerifier class."""

    def test_verifier_initialization(self):
        """Test verifier can be initialized with options."""
        from rra.verification.verifier import CodeVerifier

        verifier = CodeVerifier()
        assert verifier.timeout == 300
        assert not verifier.skip_tests
        assert not verifier.skip_security

        verifier_custom = CodeVerifier(timeout=60, skip_tests=True, skip_security=True)
        assert verifier_custom.timeout == 60
        assert verifier_custom.skip_tests
        assert verifier_custom.skip_security

    def test_verification_status_enum(self):
        """Test verification status values."""
        from rra.verification.verifier import VerificationStatus

        assert VerificationStatus.PASSED.value == "passed"
        assert VerificationStatus.WARNING.value == "warning"
        assert VerificationStatus.FAILED.value == "failed"
        assert VerificationStatus.SKIPPED.value == "skipped"

    def test_check_result_structure(self):
        """Test CheckResult dataclass."""
        from rra.verification.verifier import CheckResult, VerificationStatus

        result = CheckResult(
            name="test_check",
            status=VerificationStatus.PASSED,
            message="All tests passed",
            details={"count": 10},
        )

        assert result.name == "test_check"
        assert result.status == VerificationStatus.PASSED
        assert result.message == "All tests passed"
        assert result.details["count"] == 10

    def test_verification_result_to_dict(self):
        """Test VerificationResult serialization."""
        from rra.verification.verifier import VerificationResult, CheckResult, VerificationStatus

        result = VerificationResult(
            repo_path="/tmp/test",
            repo_url="https://github.com/test/repo",
            overall_status=VerificationStatus.PASSED,
            checks=[
                CheckResult(
                    name="tests",
                    status=VerificationStatus.PASSED,
                    message="Tests passed",
                )
            ],
            score=85.0,
            verified_at="2025-01-01T00:00:00",
        )

        data = result.to_dict()
        assert data["repo_url"] == "https://github.com/test/repo"
        assert data["overall_status"] == "passed"
        assert data["score"] == 85.0
        assert len(data["checks"]) == 1

    def test_verify_with_temp_directory(self):
        """Test verification with a temporary directory."""
        from rra.verification.verifier import CodeVerifier, VerificationStatus

        verifier = CodeVerifier(skip_tests=True, skip_security=True)

        with TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            # Create a minimal Python project
            (tmp_path / "main.py").write_text("print('hello')")
            (tmp_path / "README.md").write_text("# Test Project\n\nA test project.")
            (tmp_path / "LICENSE").write_text("MIT License")

            result = verifier.verify(
                repo_path=tmp_path,
                repo_url="https://github.com/test/repo",
                readme_content="# Test Project\n\nA test project.",
            )

            assert result.overall_status in [VerificationStatus.PASSED, VerificationStatus.WARNING]
            assert result.score >= 0
            assert len(result.checks) > 0

    def test_security_pattern_detection(self):
        """Test that security patterns are properly defined."""
        from rra.verification.verifier import CodeVerifier

        verifier = CodeVerifier()

        assert "hardcoded_secrets" in verifier.SECURITY_PATTERNS
        assert "sql_injection" in verifier.SECURITY_PATTERNS
        assert "command_injection" in verifier.SECURITY_PATTERNS
        assert len(verifier.SECURITY_PATTERNS) >= 4


class TestReadmeParser:
    """Tests for ReadmeParser class."""

    def test_parser_initialization(self):
        """Test parser initialization."""
        from rra.verification.readme_parser import ReadmeParser

        parser = ReadmeParser()
        assert parser is not None

    def test_parse_basic_readme(self):
        """Test parsing a basic README."""
        from rra.verification.readme_parser import ReadmeParser

        parser = ReadmeParser()

        readme_content = """# My Project

This is a test project for Python development.

## Features

- Feature 1
- Feature 2
- Feature 3

## Installation

```bash
pip install myproject
```

## Usage

```python
from myproject import main
main()
```
"""

        metadata = parser.parse_from_content(readme_content)

        assert metadata.title == "My Project"
        assert "test project" in metadata.description.lower()
        assert len(metadata.features) >= 3
        assert metadata.has_examples

    def test_parse_technologies(self):
        """Test technology detection from README."""
        from rra.verification.readme_parser import ReadmeParser

        parser = ReadmeParser()

        readme_content = """# My FastAPI App

Built with Python and FastAPI. Uses PostgreSQL for storage.
Frontend uses React with TypeScript.
"""

        metadata = parser.parse_from_content(readme_content)

        technologies = [t.lower() for t in metadata.technologies]
        assert "python" in technologies
        assert "fastapi" in technologies
        assert "react" in technologies

    def test_short_description_generation(self):
        """Test short description is generated correctly."""
        from rra.verification.readme_parser import ReadmeParser

        parser = ReadmeParser()

        readme_content = """# Test Project

This is the first sentence of the description. This is the second sentence that provides more details about the project and its capabilities.
"""

        metadata = parser.parse_from_content(readme_content)

        assert len(metadata.short_description) <= 150
        assert "first sentence" in metadata.short_description

    def test_metadata_to_dict(self):
        """Test ReadmeMetadata serialization."""
        from rra.verification.readme_parser import ReadmeMetadata

        metadata = ReadmeMetadata(
            title="Test",
            description="A test project",
            features=["feature1", "feature2"],
            technologies=["Python", "FastAPI"],
        )

        data = metadata.to_dict()
        assert data["title"] == "Test"
        assert len(data["features"]) == 2
        assert len(data["technologies"]) == 2


class TestCodeCategorizer:
    """Tests for CodeCategorizer class."""

    def test_categorizer_initialization(self):
        """Test categorizer initialization."""
        from rra.verification.categorizer import CodeCategorizer

        categorizer = CodeCategorizer()
        assert categorizer is not None

    def test_category_enum_values(self):
        """Test CodeCategory enum values."""
        from rra.verification.categorizer import CodeCategory

        assert CodeCategory.LIBRARY.value == "library"
        assert CodeCategory.CLI_TOOL.value == "cli_tool"
        assert CodeCategory.WEB_APP.value == "web_app"
        assert CodeCategory.API_SERVICE.value == "api_service"
        assert CodeCategory.SMART_CONTRACT.value == "smart_contract"

    def test_subcategory_enum_values(self):
        """Test SubCategory enum values."""
        from rra.verification.categorizer import SubCategory

        assert SubCategory.FRONTEND.value == "frontend"
        assert SubCategory.BACKEND.value == "backend"
        assert SubCategory.MACHINE_LEARNING.value == "machine_learning"
        assert SubCategory.DEFI.value == "defi"

    def test_categorize_python_library(self):
        """Test categorization of a Python library."""
        from rra.verification.categorizer import CodeCategorizer

        categorizer = CodeCategorizer()

        with TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            # Create a library-like structure
            (tmp_path / "pyproject.toml").write_text('[project]\nname = "mylib"')
            (tmp_path / "src").mkdir()
            (tmp_path / "src" / "__init__.py").write_text("")
            (tmp_path / "src" / "core.py").write_text("class MyClass:\n    pass")

            result = categorizer.categorize(
                repo_path=tmp_path,
                dependencies={"python": ["pydantic", "typing-extensions"]},
            )

            # Should detect as library
            assert result.confidence > 0
            assert "Python" in result.technologies

    def test_categorize_cli_tool(self):
        """Test categorization of a CLI tool."""
        from rra.verification.categorizer import CodeCategorizer, CodeCategory

        categorizer = CodeCategorizer()

        with TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            # Create a CLI-like structure
            (tmp_path / "cli.py").write_text("import click\n@click.command()\ndef main():\n    pass")
            (tmp_path / "__main__.py").write_text("from cli import main\nmain()")

            result = categorizer.categorize(
                repo_path=tmp_path,
                dependencies={"python": ["click", "rich"]},
            )

            # Should detect CLI signals
            assert result.primary_category in [CodeCategory.CLI_TOOL, CodeCategory.LIBRARY]
            assert result.confidence > 0

    def test_category_result_to_dict(self):
        """Test CategoryResult serialization."""
        from rra.verification.categorizer import CategoryResult, CodeCategory, SubCategory

        result = CategoryResult(
            primary_category=CodeCategory.WEB_APP,
            subcategory=SubCategory.FRONTEND,
            confidence=0.85,
            tags=["react", "typescript"],
            technologies=["JavaScript", "TypeScript"],
            frameworks=["React", "Next.js"],
            reasoning="Detected React and Next.js",
        )

        data = result.to_dict()
        assert data["primary_category"] == "web_app"
        assert data["subcategory"] == "frontend"
        assert data["confidence"] == 0.85
        assert "react" in data["tags"]


class TestBlockchainLinkGenerator:
    """Tests for BlockchainLinkGenerator class."""

    def test_generator_initialization(self):
        """Test generator initialization with different networks."""
        from rra.verification.blockchain_link import BlockchainLinkGenerator, NetworkType

        # Test testnet (default)
        gen = BlockchainLinkGenerator()
        assert gen.network == NetworkType.TESTNET
        assert "testnet" in gen.marketplace_url

        # Test mainnet
        gen_mainnet = BlockchainLinkGenerator(network=NetworkType.MAINNET)
        assert gen_mainnet.network == NetworkType.MAINNET

        # Test localhost
        gen_local = BlockchainLinkGenerator(network=NetworkType.LOCALHOST)
        assert gen_local.network == NetworkType.LOCALHOST
        assert "localhost" in gen_local.marketplace_url

    def test_generate_ip_asset_id(self):
        """Test IP Asset ID generation is deterministic."""
        from rra.verification.blockchain_link import BlockchainLinkGenerator

        gen = BlockchainLinkGenerator()

        repo_url = "https://github.com/test/repo"
        wallet = "0x1234567890abcdef1234567890abcdef12345678"

        id1 = gen.generate_ip_asset_id(repo_url, wallet)
        id2 = gen.generate_ip_asset_id(repo_url, wallet)

        # Should be deterministic
        assert id1 == id2
        assert id1.startswith("0x")
        assert len(id1) == 66  # 0x + 64 hex chars

    def test_generate_purchase_link(self):
        """Test purchase link generation."""
        from rra.verification.blockchain_link import BlockchainLinkGenerator, LicenseTier

        gen = BlockchainLinkGenerator()

        repo_url = "https://github.com/test/repo"
        ip_asset_id = "0x" + "a" * 64

        link = gen.generate_purchase_link(
            repo_url=repo_url,
            ip_asset_id=ip_asset_id,
            tier=LicenseTier.STANDARD,
            price_eth=0.05,
        )

        assert "purchase" in link.url
        assert link.tier == LicenseTier.STANDARD
        assert link.price_display == "0.05 ETH"
        assert link.ip_asset_id == ip_asset_id

    def test_generate_all_tier_links(self):
        """Test generation of links for all tiers."""
        from rra.verification.blockchain_link import BlockchainLinkGenerator

        gen = BlockchainLinkGenerator()

        repo_url = "https://github.com/test/repo"
        ip_asset_id = "0x" + "b" * 64

        pricing = {
            "standard": 0.05,
            "premium": 0.15,
            "enterprise": 0.50,
        }

        links = gen.generate_all_tier_links(
            repo_url=repo_url,
            ip_asset_id=ip_asset_id,
            pricing=pricing,
        )

        assert len(links) == 3
        tiers = {link.tier.value for link in links}
        assert "standard" in tiers
        assert "premium" in tiers
        assert "enterprise" in tiers

    def test_generate_explorer_link(self):
        """Test explorer link generation."""
        from rra.verification.blockchain_link import BlockchainLinkGenerator, NetworkType

        gen = BlockchainLinkGenerator(network=NetworkType.MAINNET)

        ip_asset_id = "0x" + "c" * 64
        link = gen.generate_explorer_link(ip_asset_id)

        assert ip_asset_id in link
        assert "explorer" in link

    def test_purchase_link_to_dict(self):
        """Test PurchaseLink serialization."""
        from rra.verification.blockchain_link import PurchaseLink, NetworkType, LicenseTier

        link = PurchaseLink(
            url="https://example.com/purchase",
            network=NetworkType.TESTNET,
            ip_asset_id="0x" + "d" * 64,
            tier=LicenseTier.PREMIUM,
            price_wei=150000000000000000,  # 0.15 ETH
            price_display="0.15 ETH",
        )

        data = link.to_dict()
        assert data["tier"] == "premium"
        assert data["network"] == "testnet"
        assert "0.15" in data["price_display"]

    def test_purchase_link_to_markdown(self):
        """Test PurchaseLink markdown generation."""
        from rra.verification.blockchain_link import PurchaseLink, NetworkType, LicenseTier

        link = PurchaseLink(
            url="https://example.com/purchase",
            network=NetworkType.TESTNET,
            ip_asset_id="0x" + "e" * 64,
            tier=LicenseTier.ENTERPRISE,
            price_display="0.50 ETH",
        )

        md = link.to_markdown()
        assert "[" in md and "](" in md  # Markdown link format
        assert "Enterprise" in md
        assert "0.50 ETH" in md

    def test_generate_marketplace_listing(self):
        """Test complete marketplace listing generation."""
        from rra.verification.blockchain_link import BlockchainLinkGenerator

        gen = BlockchainLinkGenerator()

        listing = gen.generate_marketplace_listing(
            repo_url="https://github.com/test/repo",
            repo_name="repo",
            description="A test repository",
            category="library",
            owner_address="0x1234567890abcdef1234567890abcdef12345678",
            pricing={"standard": 0.05, "premium": 0.15},
            verification_score=85.0,
            tags=["python", "library"],
            technologies=["Python"],
        )

        assert listing.repo_name == "repo"
        assert listing.category == "library"
        assert listing.verification_score == 85.0
        assert len(listing.purchase_links) == 2
        assert len(listing.tags) == 2

    def test_generate_embed_widget(self):
        """Test embed widget HTML generation."""
        from rra.verification.blockchain_link import BlockchainLinkGenerator

        gen = BlockchainLinkGenerator()

        listing = gen.generate_marketplace_listing(
            repo_url="https://github.com/test/repo",
            repo_name="repo",
            description="A test repository",
            category="library",
            owner_address="0x1234567890abcdef1234567890abcdef12345678",
            pricing={"standard": 0.05},
        )

        html = gen.generate_embed_widget(listing, theme="dark")

        assert "rra-widget" in html
        assert "dark" in html
        assert "repo" in html
        assert "<style>" in html


class TestIntegration:
    """Integration tests for the verification module."""

    def test_full_verification_flow(self):
        """Test complete verification flow with all components."""
        from rra.verification.verifier import CodeVerifier
        from rra.verification.readme_parser import ReadmeParser
        from rra.verification.categorizer import CodeCategorizer
        from rra.verification.blockchain_link import BlockchainLinkGenerator

        with TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            # Create a comprehensive Python project
            (tmp_path / "main.py").write_text(
                "import click\n\n@click.command()\ndef main():\n    print('Hello')\n\nif __name__ == '__main__':\n    main()"
            )
            (tmp_path / "requirements.txt").write_text("click>=8.0\nrich>=13.0")
            (tmp_path / "README.md").write_text(
                "# My CLI Tool\n\nA command-line tool built with Python and Click.\n\n## Features\n\n- Feature 1\n- Feature 2"
            )
            (tmp_path / "LICENSE").write_text("MIT License")
            (tmp_path / "test_main.py").write_text("def test_main():\n    assert True")

            # Parse README
            parser = ReadmeParser()
            readme = parser.parse(tmp_path / "README.md")
            assert readme.title == "My CLI Tool"
            assert len(readme.features) >= 2

            # Verify code
            verifier = CodeVerifier(skip_tests=True)
            verification = verifier.verify(
                repo_path=tmp_path,
                repo_url="https://github.com/test/cli-tool",
                readme_content=(tmp_path / "README.md").read_text(),
            )
            assert verification.score > 0
            assert len(verification.checks) >= 5

            # Categorize
            categorizer = CodeCategorizer()
            category = categorizer.categorize(
                repo_path=tmp_path,
                readme_content=(tmp_path / "README.md").read_text(),
                dependencies={"python": ["click", "rich"]},
            )
            assert category.confidence > 0
            assert "Python" in category.technologies

            # Generate blockchain links
            gen = BlockchainLinkGenerator()
            listing = gen.generate_marketplace_listing(
                repo_url="https://github.com/test/cli-tool",
                repo_name="cli-tool",
                description=readme.short_description,
                category=category.primary_category.value,
                owner_address="0x1234567890abcdef1234567890abcdef12345678",
                pricing={"standard": 0.05, "premium": 0.15, "enterprise": 0.50},
                verification_score=verification.score,
                tags=category.tags,
                technologies=category.technologies,
            )

            assert listing.verification_score == verification.score
            assert len(listing.purchase_links) == 3
