# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Main CLI entry point for RRA Module.

Provides commands for:
- Initializing repositories with .market.yaml
- Ingesting repositories
- Starting negotiation sessions
- Managing agents
"""

import json
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown

from rra import __version__
from rra.config.market_config import (
    MarketConfig,
    LicenseModel,
    NegotiationStyle,
)
from rra.ingestion.repo_ingester import RepoIngester
from rra.agents.negotiator import NegotiatorAgent
from rra.agents.buyer import BuyerAgent
from rra.status.dreaming import get_dreaming_status
from rra.status.cli_integration import enable_dreaming_output, get_dreaming_summary


console = Console()


@click.group()
@click.version_option(version=__version__)
@click.option("--dreaming/--no-dreaming", default=True, help="Show dreaming status updates")
@click.pass_context
def cli(ctx, dreaming):
    """
    RRA Module - Revenant Repo Agent

    Transform dormant repositories into autonomous licensing agents.
    """
    ctx.ensure_object(dict)
    ctx.obj["dreaming"] = dreaming

    if dreaming:
        enable_dreaming_output(console)


@cli.command()
@click.argument("repo_path", type=click.Path(exists=True, path_type=Path))
@click.option("--target-price", default="0.05 ETH", help="Target price for licensing")
@click.option("--floor-price", default="0.02 ETH", help="Minimum acceptable price")
@click.option(
    "--license-model",
    type=click.Choice(["per-seat", "subscription", "one-time", "perpetual", "custom"]),
    default="per-seat",
)
@click.option(
    "--negotiation-style",
    type=click.Choice(["concise", "persuasive", "strict", "adaptive"]),
    default="concise",
)
@click.option("--wallet", help="Ethereum wallet address for payments")
def init(
    repo_path: Path,
    target_price: str,
    floor_price: str,
    license_model: str,
    negotiation_style: str,
    wallet: Optional[str],
):
    """
    Initialize a repository with RRA configuration.

    Creates a .market.yaml file with the specified settings.
    """
    console.print(
        Panel.fit(
            f"[bold blue]Initializing RRA for repository[/bold blue]\n{repo_path}",
            border_style="blue",
        )
    )

    # Create configuration
    config = MarketConfig(
        target_price=target_price,
        floor_price=floor_price,
        license_model=LicenseModel(license_model),
        negotiation_style=NegotiationStyle(negotiation_style),
        allow_custom_fork_rights=True,
        description="Automated licensing for this repository",
        features=["Full source code access", "Regular updates", "Developer support"],
    )

    if wallet:
        config.developer_wallet = wallet

    # Save configuration
    config_path = repo_path / ".market.yaml"
    config.to_yaml(config_path)

    console.print(f"\n[green]✓[/green] Created configuration: {config_path}")
    console.print("\n[bold]Next steps:[/bold]")
    console.print("  1. Review and customize .market.yaml")
    console.print("  2. Run: rra ingest <repo-url> to create knowledge base")
    console.print("  3. Run: rra agent start <repo-url> to launch negotiation agent")


@cli.command()
@click.argument("repo_url")
@click.option(
    "--workspace",
    type=click.Path(path_type=Path),
    default=Path("./cloned_repos"),
    help="Directory for cloned repos",
)
@click.option("--force", is_flag=True, help="Force refresh by re-cloning")
@click.option("--verify/--no-verify", default=True, help="Run code verification")
@click.option("--categorize/--no-categorize", default=True, help="Auto-categorize the repository")
@click.option("--wallet", help="Ethereum wallet address for blockchain links")
@click.option(
    "--network",
    type=click.Choice(["mainnet", "testnet", "localhost"]),
    default="testnet",
    help="Blockchain network",
)
@click.option(
    "--timeout",
    type=int,
    default=300,
    help="Timeout in seconds for test execution (default: 300)",
)
@click.option(
    "--auto-install-deps",
    is_flag=True,
    help="Automatically install dependencies in temp environment for testing",
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Show verbose output including full test/lint errors",
)
@click.option(
    "--no-cache",
    is_flag=True,
    help="Disable dependency caching (create fresh venv each time)",
)
@click.option(
    "--clear-cache",
    is_flag=True,
    help="Clear dependency cache before running",
)
def ingest(
    repo_url: str,
    workspace: Path,
    force: bool,
    verify: bool,
    categorize: bool,
    wallet: Optional[str],
    network: str,
    timeout: int,
    auto_install_deps: bool,
    verbose: bool,
    no_cache: bool,
    clear_cache: bool,
):
    """
    Ingest a repository and generate its knowledge base.

    Clones the repository, parses its contents, and creates a structured
    knowledge base for agent reasoning.

    Now includes:
    - Code verification (tests, linting, security)
    - Automatic categorization
    - Blockchain purchase link generation
    """
    console.print(
        Panel.fit(f"[bold blue]Ingesting Repository[/bold blue]\n{repo_url}", border_style="blue")
    )

    try:
        # Handle cache clearing
        if clear_cache:
            from rra.verification.dependency_installer import DependencyInstaller
            console.print("[bold blue]Clearing dependency cache...[/bold blue]")
            installer = DependencyInstaller()
            cache_size = installer.get_cache_size()
            installer.clear_cache()
            console.print(f"[green]✓[/green] Cleared {cache_size / 1024 / 1024:.1f} MB from cache")

        with console.status("[bold blue]Ingesting repository...", spinner="dots"):
            ingester = RepoIngester(
                workspace_dir=workspace,
                verify_code=verify,
                categorize=categorize,
                generate_blockchain_links=bool(wallet),
                owner_address=wallet,
                network=network,
                test_timeout=timeout,
                auto_install_deps=auto_install_deps,
                use_cache=not no_cache,
            )
            kb = ingester.ingest(repo_url, force_refresh=force)

        # Save knowledge base
        kb_path = kb.save()

        console.print(f"\n[green]✓[/green] Knowledge base created: {kb_path}")

        # Display summary
        console.print("\n[bold]Repository Summary:[/bold]")
        console.print(Panel(kb.get_summary(), border_style="green"))

        # Show verification results
        if kb.verification:
            console.print("\n[bold]Verification Results:[/bold]")
            score = kb.verification.get("score", 0)
            status = kb.verification.get("overall_status", "unknown")
            color = "green" if status == "passed" else ("yellow" if status == "warning" else "red")
            console.print(f"  Score: [{color}]{score}/100[/{color}]")
            console.print(f"  Status: [{color}]{status}[/{color}]")

            # Check descriptions for verbose mode
            check_descriptions = {
                "tests": "Runs test suite to verify code correctness",
                "linting": "Checks code style and quality standards",
                "security": "Scans for hardcoded secrets, SQL injection, command injection",
                "build": "Validates build configuration files",
                "readme_alignment": "Verifies README claims match actual code",
                "documentation": "Checks for README and doc files",
                "license": "Verifies license file exists",
                "cicd": "Checks for CI/CD configuration (GitHub Actions, etc.)",
                "maturity": "Analyzes repository age, commit frequency, contributors",
                "completeness": "Checks for changelog, examples, Docker, contributing guides",
            }

            for check in kb.verification.get("checks", []):
                check_color = (
                    "green"
                    if check["status"] == "passed"
                    else ("yellow" if check["status"] == "warning" else "red")
                )
                status_icon = (
                    "✓" if check["status"] == "passed"
                    else ("⚠" if check["status"] == "warning" else "✗")
                )
                console.print(
                    f"    [{check_color}]{status_icon}[/{check_color}] {check['name']}: {check['message']}"
                )

                # Show verbose details
                if verbose and check.get("details"):
                    details = check["details"]

                    # Show description
                    if check["name"] in check_descriptions:
                        console.print(f"      [dim]→ {check_descriptions[check['name']]}[/dim]")

                    # Show test output/errors
                    if check["name"] == "tests":
                        if details.get("error"):
                            console.print("      [dim]Test output (showing end where failures appear):[/dim]")
                            # Show END of error output (that's where pytest shows failures)
                            error_text = details["error"]
                            if len(error_text) > 3000:
                                error_text = "... (earlier output truncated)\n" + error_text[-3000:]
                            for line in error_text.split("\n")[-60:]:
                                if line.strip():
                                    console.print(f"        {line}")
                        if details.get("output"):
                            console.print("      [dim]Test output:[/dim]")
                            output_text = details["output"][-1500:]  # Show end
                            for line in output_text.split("\n")[-40:]:
                                if line.strip():
                                    console.print(f"        {line}")
                        if details.get("warning"):
                            console.print(f"      [yellow]Note: {details['warning']}[/yellow]")
                        console.print(f"      [dim]Test files: {details.get('test_files', 0)}, Test cases: ~{details.get('test_count', 0)}[/dim]")

                    # Show linting details
                    elif check["name"] == "linting":
                        if details.get("output"):
                            console.print("      [dim]Linting output:[/dim]")
                            output_text = details["output"][:1500]
                            for line in output_text.split("\n")[:40]:
                                if line.strip():
                                    console.print(f"        {line}")
                        if details.get("issues"):
                            console.print(f"      [dim]Total issues: {details['issues']}[/dim]")
                        if details.get("has_config"):
                            console.print("      [dim]Lint config found: Yes[/dim]")

                    # Show security details
                    elif check["name"] == "security":
                        console.print(f"      [dim]Files scanned: {details.get('files_scanned', 0)}[/dim]")
                        if details.get("issues"):
                            console.print("      [yellow]Issues found:[/yellow]")
                            for issue in details.get("issues", [])[:10]:
                                console.print(f"        [{issue.get('category')}] {issue.get('file')}")
                        if details.get("issues_by_category"):
                            for cat, count in details["issues_by_category"].items():
                                console.print(f"        {cat}: {count} issues")

                    # Show build details
                    elif check["name"] == "build":
                        if details.get("build_systems"):
                            systems = [b["language"] for b in details["build_systems"]]
                            console.print(f"      [dim]Build systems: {', '.join(systems)}[/dim]")

                    # Show README alignment details
                    elif check["name"] == "readme_alignment":
                        if details.get("verified_claims"):
                            console.print("      [green]Verified claims:[/green]")
                            for claim in details["verified_claims"][:5]:
                                console.print(f"        ✓ {claim.get('claim', claim)[:60]}")
                        if details.get("unverified_claims"):
                            console.print("      [yellow]Unverified claims:[/yellow]")
                            for claim in details["unverified_claims"][:5]:
                                console.print(f"        ? {claim.get('claim', claim)[:60]}")

                    # Show CI/CD details
                    elif check["name"] == "cicd":
                        if details.get("ci_systems"):
                            console.print(f"      [dim]CI Systems: {', '.join(details['ci_systems'])}[/dim]")
                        if details.get("workflow_count"):
                            console.print(f"      [dim]Workflows: {details['workflow_count']}[/dim]")

                    # Show maturity details
                    elif check["name"] == "maturity":
                        if details.get("age_days") is not None:
                            console.print(f"      [dim]Age: {details['age_days']} days[/dim]")
                        if details.get("total_commits"):
                            console.print(f"      [dim]Commits: {details['total_commits']}[/dim]")
                        if details.get("commits_per_month"):
                            console.print(f"      [dim]Commits/month: {details['commits_per_month']}[/dim]")
                        if details.get("contributors"):
                            console.print(f"      [dim]Contributors: {details['contributors']}[/dim]")
                        if details.get("days_since_last_commit") is not None:
                            console.print(f"      [dim]Last commit: {details['days_since_last_commit']} days ago[/dim]")

                    # Show completeness details
                    elif check["name"] == "completeness":
                        if details.get("found"):
                            console.print(f"      [green]Found: {', '.join(details['found'])}[/green]")
                        if details.get("missing"):
                            console.print(f"      [yellow]Missing: {', '.join(details['missing'])}[/yellow]")

        # Show category
        if kb.category:
            console.print("\n[bold]Category:[/bold]")
            console.print(
                f"  Primary: [cyan]{kb.category.get('primary_category', 'unknown')}[/cyan]"
            )
            if kb.category.get("subcategory"):
                console.print(f"  Subcategory: {kb.category.get('subcategory')}")
            if kb.category.get("tags"):
                tags = ", ".join(kb.category.get("tags", [])[:5])
                console.print(f"  Tags: {tags}")

        # Show blockchain links
        if kb.blockchain_links:
            console.print("\n[bold]Blockchain Links:[/bold]")
            console.print(f"  IP Asset ID: [cyan]{kb.blockchain_links.get('ip_asset_id')}[/cyan]")
            for link in kb.blockchain_links.get("purchase_links", []):
                console.print(f"  {link['tier'].capitalize()}: {link['url']}")

        # Show negotiation context
        context = kb.get_negotiation_context()
        if context.get("value_propositions"):
            console.print("\n[bold]Value Propositions:[/bold]")
            for prop in context["value_propositions"]:
                console.print(f"  • {prop}")

    except Exception as e:
        console.print(f"[red]✗[/red] Ingestion failed: {e}", style="bold red")
        sys.exit(1)


@cli.command()
@click.argument("kb_path", type=click.Path(exists=True, path_type=Path))
@click.option("--interactive", is_flag=True, help="Start interactive negotiation session")
@click.option("--simulate", is_flag=True, help="Run simulation with buyer agent")
def agent(kb_path: Path, interactive: bool, simulate: bool):
    """
    Start a negotiation agent for a repository.

    Loads the knowledge base and starts an autonomous negotiation agent.
    """
    from rra.ingestion.knowledge_base import KnowledgeBase

    console.print(
        Panel.fit("[bold blue]Starting Negotiation Agent[/bold blue]", border_style="blue")
    )

    try:
        # Load knowledge base
        with console.status("[bold blue]Loading knowledge base...", spinner="dots"):
            kb = KnowledgeBase.load(kb_path)

        console.print(f"[green]✓[/green] Loaded: {kb.repo_url}\n")

        # Create negotiator
        negotiator = NegotiatorAgent(kb)

        if simulate:
            # Run simulation
            console.print("[bold]Running negotiation simulation...[/bold]\n")

            buyer = BuyerAgent(name="SimulatedBuyer")
            buyer.set_budget("0.04 ETH")
            buyer.add_requirement("API access")

            result = buyer.simulate_negotiation(negotiator, strategy="haggle")

            console.print("\n[bold]Simulation Complete![/bold]")
            console.print(f"Messages exchanged: {result['messages_exchanged']}")

            # Show history
            console.print("\n[bold]Negotiation History:[/bold]")
            for interaction in buyer.get_interaction_history():
                direction = "→" if interaction["direction"] == "sent" else "←"
                console.print(f"\n{direction} {interaction['content'][:150]}...")

        elif interactive:
            # Interactive session
            console.print("[bold]Starting interactive negotiation session[/bold]")
            console.print("Type 'quit' to exit\n")

            # Start negotiation
            intro = negotiator.start_negotiation()
            console.print(f"[blue]Negotiator:[/blue] {intro}\n")

            while True:
                # Get user input
                user_input = console.input("[green]You:[/green] ")

                if user_input.lower() in ["quit", "exit", "q"]:
                    break

                # Get response
                response = negotiator.respond(user_input)
                console.print(f"\n[blue]Negotiator:[/blue] {response}\n")

            # Show summary
            summary = negotiator.get_negotiation_summary()
            console.print("\n[bold]Negotiation Summary:[/bold]")
            console.print(f"Phase: {summary['phase']}")
            console.print(f"Messages: {summary['message_count']}")

        else:
            # Just show agent info
            intro = negotiator.start_negotiation()
            console.print("[bold]Agent Introduction:[/bold]")
            console.print(Panel(intro, border_style="blue"))

            console.print("\n[bold]Agent ready![/bold]")
            console.print("Use --interactive for manual negotiation")
            console.print("Use --simulate for automated simulation")

    except Exception as e:
        console.print(f"[red]✗[/red] Failed to start agent: {e}", style="bold red")
        sys.exit(1)


@cli.command()
@click.option(
    "--workspace", type=click.Path(path_type=Path), default=Path("./agent_knowledge_bases")
)
def list(workspace: Path):
    """
    List all ingested repositories and their knowledge bases.
    """
    if not workspace.exists():
        console.print("[yellow]No knowledge bases found[/yellow]")
        return

    kb_files = list(workspace.glob("*_kb.json"))

    if not kb_files:
        console.print("[yellow]No knowledge bases found[/yellow]")
        return

    from rra.ingestion.knowledge_base import KnowledgeBase

    table = Table(title="Ingested Repositories")
    table.add_column("Repository", style="cyan")
    table.add_column("Files", justify="right")
    table.add_column("Languages", style="green")
    table.add_column("Updated", style="yellow")

    for kb_file in kb_files:
        try:
            kb = KnowledgeBase.load(kb_file)

            repo_name = kb.repo_url.split("/")[-1]
            files = kb.statistics.get("code_files", 0)
            languages = ", ".join(kb.statistics.get("languages", [])[:3])
            updated = kb.updated_at.strftime("%Y-%m-%d")

            table.add_row(repo_name, str(files), languages, updated)
        except (json.JSONDecodeError, KeyError, AttributeError, OSError) as e:
            # Skip corrupted or invalid knowledge base files
            console.print(f"[dim]Skipping {kb_file.name}: {e}[/dim]")

    console.print(table)


@cli.command()
@click.argument("kb_path", type=click.Path(exists=True, path_type=Path))
def info(kb_path: Path):
    """
    Display detailed information about a knowledge base.
    """
    from rra.ingestion.knowledge_base import KnowledgeBase

    try:
        kb = KnowledgeBase.load(kb_path)

        console.print(Panel(kb.get_summary(), title="Repository Information", border_style="blue"))

        # Show market config details
        if kb.market_config:
            config_table = Table(title="Market Configuration")
            config_table.add_column("Setting", style="cyan")
            config_table.add_column("Value", style="green")

            config_table.add_row("License Model", kb.market_config.license_model.value)
            config_table.add_row("Target Price", kb.market_config.target_price)
            config_table.add_row("Floor Price", kb.market_config.floor_price)
            config_table.add_row("Negotiation Style", kb.market_config.negotiation_style.value)

            console.print(config_table)

    except Exception as e:
        console.print(f"[red]✗[/red] Error loading knowledge base: {e}", style="bold red")
        sys.exit(1)


@cli.command()
def example():
    """
    Show example .market.yaml configuration.
    """
    example_yaml = """# .market.yaml - RRA Module Configuration

license_model: "per-seat"  # Options: per-seat, subscription, one-time, perpetual, custom
target_price: "0.05 ETH"   # Suggested starting price
floor_price: "0.02 ETH"    # Minimum acceptable price

negotiation_style: "concise"  # Options: concise, persuasive, strict, adaptive

allow_custom_fork_rights: true
auto_renewal: false

# Optional settings
description: "Production-ready API framework with extensive documentation"
features:
  - "Full source code access"
  - "Regular updates and bug fixes"
  - "Developer support via GitHub issues"
  - "Commercial use permitted"

update_frequency: "weekly"  # Options: daily, weekly, monthly, on-push
sandbox_tests: "tests/verification.py"  # Path to verification scripts

# Blockchain settings
developer_wallet: "0x1234..."  # Your Ethereum address
royalty_on_derivatives: 0.15   # 15% royalty on forks/derivatives

# Additional metadata
metadata:
  category: "web-framework"
  maturity: "production"
"""

    console.print(Panel(Markdown(example_yaml), title="Example .market.yaml", border_style="blue"))

    console.print("\n[bold]Quick Start:[/bold]")
    console.print("  1. Create .market.yaml in your repo root")
    console.print("  2. Run: rra init <repo-path>")
    console.print("  3. Customize the generated configuration")


@cli.command()
@click.argument("repo_url")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json", "markdown"]),
    default="table",
    help="Output format",
)
@click.option("--register", is_flag=True, help="Register the repository for permanent linking")
def links(repo_url: str, output_format: str, register: bool):
    """
    Generate shareable deep links for a repository.

    Creates URLs for:
    - Agent page (for browsing)
    - Direct chat (starts negotiation immediately)
    - License tiers (specific tier purchase)
    - QR codes (for print/sharing)
    - README badges (for documentation)
    - Embed codes (for websites)
    """
    from rra.services.deep_links import DeepLinkService
    import json

    console.print(
        Panel.fit(f"[bold blue]Generating Deep Links[/bold blue]\n{repo_url}", border_style="blue")
    )

    service = DeepLinkService()

    # Register if requested
    if register:
        service.register_repo(repo_url)
        console.print("[green]✓[/green] Repository registered for permanent linking\n")

    # Get all links
    all_links = service.get_all_links(repo_url)

    if output_format == "json":
        console.print(json.dumps(all_links, indent=2))

    elif output_format == "markdown":
        md = f"""# Deep Links for Repository

**Repository ID:** `{all_links['repo_id']}`

## Quick Links

| Type | URL |
|------|-----|
| Agent Page | [{all_links['agent_page']}]({all_links['agent_page']}) |
| Direct Chat | [{all_links['chat_direct']}]({all_links['chat_direct']}) |
| Individual License | [{all_links['license_individual']}]({all_links['license_individual']}) |
| Team License | [{all_links['license_team']}]({all_links['license_team']}) |
| Enterprise License | [{all_links['license_enterprise']}]({all_links['license_enterprise']}) |

## QR Code

![QR Code]({all_links['qr_code']})

## README Badge

```markdown
{all_links['badge_markdown']}
```

## Embed Code

```html
{all_links['embed_script']}
```
"""
        console.print(Markdown(md))

    else:  # table format
        # Basic links table
        table = Table(title="Generated Links", show_header=True)
        table.add_column("Type", style="cyan", width=20)
        table.add_column("URL/Value", style="green")

        table.add_row("Repository ID", all_links["repo_id"])
        table.add_row("Agent Page", all_links["agent_page"])
        table.add_row("Direct Chat", all_links["chat_direct"])
        table.add_row("Individual License", all_links["license_individual"])
        table.add_row("Team License", all_links["license_team"])
        table.add_row("Enterprise License", all_links["license_enterprise"])
        table.add_row("QR Code (PNG)", all_links["qr_code"])

        console.print(table)

        # Badge section
        console.print("\n[bold]README Badge (Markdown):[/bold]")
        console.print(Panel(all_links["badge_markdown"], border_style="dim"))

        # Embed section
        console.print("\n[bold]Embed Code (HTML):[/bold]")
        console.print(Panel(all_links["embed_script"], border_style="dim"))


@cli.command()
@click.argument("repo_id")
def resolve(repo_id: str):
    """
    Resolve a repository ID to its original URL.

    Looks up a 12-character repo ID and shows its registration info.
    """
    from rra.services.deep_links import DeepLinkService

    service = DeepLinkService()
    mapping = service.resolve_repo_id(repo_id)

    if mapping:
        table = Table(title=f"Repository: {repo_id}")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="green")

        for key, value in mapping.items():
            table.add_row(key, str(value))

        console.print(table)
    else:
        console.print(f"[yellow]Repository ID not found: {repo_id}[/yellow]")
        console.print(
            "\nThis ID may not be registered. Use 'rra links <repo-url> --register' to register a repository."
        )


@cli.command()
@click.argument("repo_url")
@click.option("--skip-tests", is_flag=True, help="Skip running actual tests")
@click.option("--skip-security", is_flag=True, help="Skip security scanning")
@click.option(
    "--workspace",
    type=click.Path(path_type=Path),
    default=Path("./cloned_repos"),
    help="Directory for cloned repos",
)
@click.option(
    "--timeout",
    type=int,
    default=300,
    help="Timeout in seconds for test execution (default: 300)",
)
@click.option(
    "--auto-install-deps",
    is_flag=True,
    help="Automatically install dependencies in temp environment for testing",
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Show verbose output including full test/lint errors",
)
@click.option(
    "--no-cache",
    is_flag=True,
    help="Disable dependency caching (create fresh venv each time)",
)
@click.option(
    "--clear-cache",
    is_flag=True,
    help="Clear dependency cache before running",
)
def verify(repo_url: str, skip_tests: bool, skip_security: bool, workspace: Path, timeout: int, auto_install_deps: bool, verbose: bool, no_cache: bool, clear_cache: bool):
    """
    Verify a GitHub repository's code quality.

    Runs comprehensive verification including:
    - Test suite detection and execution
    - Linting and code quality checks
    - Security vulnerability scanning
    - Build/installation verification
    - README alignment checking
    """
    from rra.verification.verifier import CodeVerifier

    console.print(
        Panel.fit(f"[bold blue]Verifying Repository[/bold blue]\n{repo_url}", border_style="blue")
    )

    try:
        # Handle cache clearing
        if clear_cache:
            from rra.verification.dependency_installer import DependencyInstaller
            console.print("[bold blue]Clearing dependency cache...[/bold blue]")
            installer = DependencyInstaller()
            cache_size = installer.get_cache_size()
            installer.clear_cache()
            console.print(f"[green]✓[/green] Cleared {cache_size / 1024 / 1024:.1f} MB from cache")

        # Clone the repo first
        with console.status("[bold blue]Cloning repository...", spinner="dots"):
            ingester = RepoIngester(
                workspace_dir=workspace,
                verify_code=False,
                categorize=False,
                generate_blockchain_links=False,
            )
            kb = ingester.ingest(repo_url)

        # Run verification
        console.print("\n[bold]Running verification checks...[/bold]\n")

        verifier = CodeVerifier(
            timeout=timeout,
            skip_tests=skip_tests,
            skip_security=skip_security,
            auto_install_deps=auto_install_deps,
            use_cache=not no_cache,
        )

        readme_content = kb.documentation.get("README.md", "")

        result = verifier.verify(
            repo_path=kb.repo_path,
            repo_url=repo_url,
            readme_content=readme_content,
        )

        # Display results
        score = result.score
        status = result.overall_status.value
        status_color = (
            "green" if status == "passed" else ("yellow" if status == "warning" else "red")
        )

        console.print(f"[bold]Overall Score:[/bold] [{status_color}]{score}/100[/{status_color}]")
        console.print(f"[bold]Status:[/bold] [{status_color}]{status.upper()}[/{status_color}]")

        console.print("\n[bold]Detailed Checks:[/bold]\n")

        table = Table(show_header=True)
        table.add_column("Check", style="cyan", width=20)
        table.add_column("Status", width=10)
        table.add_column("Message", style="dim")

        for check in result.checks:
            check_color = (
                "green"
                if check.status.value == "passed"
                else ("yellow" if check.status.value == "warning" else "red")
            )
            status_icon = (
                "✓"
                if check.status.value == "passed"
                else ("⚠" if check.status.value == "warning" else "✗")
            )
            table.add_row(
                check.name.replace("_", " ").title(),
                f"[{check_color}]{status_icon} {check.status.value}[/{check_color}]",
                check.message[:60] + "..." if len(check.message) > 60 else check.message,
            )

        console.print(table)

        # Show verbose details for each check
        if verbose:
            check_descriptions = {
                "tests": "Runs test suite to verify code correctness",
                "linting": "Checks code style and quality standards",
                "security": "Scans for hardcoded secrets, SQL injection, command injection",
                "build": "Validates build configuration files",
                "readme_alignment": "Verifies README claims match actual code",
                "documentation": "Checks for README and doc files",
                "license": "Verifies license file exists",
                "cicd": "Checks for CI/CD configuration (GitHub Actions, etc.)",
                "maturity": "Analyzes repository age, commit frequency, contributors",
                "completeness": "Checks for changelog, examples, Docker, contributing guides",
            }

            console.print("\n[bold]Detailed Output:[/bold]\n")

            for check in result.checks:
                check_color = (
                    "green" if check.status.value == "passed"
                    else ("yellow" if check.status.value == "warning" else "red")
                )
                console.print(f"[{check_color}]━━━ {check.name.upper()} ━━━[/{check_color}]")

                if check.name in check_descriptions:
                    console.print(f"[dim]{check_descriptions[check.name]}[/dim]")

                console.print(f"Status: {check.status.value}")
                console.print(f"Message: {check.message}")

                if check.details:
                    details = check.details

                    if check.name == "tests":
                        if details.get("error"):
                            console.print("\n[bold]Test Error Output:[/bold]")
                            error_text = details["error"][:3000]
                            for line in error_text.split("\n")[:60]:
                                console.print(f"  {line}")
                            if len(details["error"]) > 3000:
                                console.print(f"  [dim]... (truncated, {len(details['error'])} chars total)[/dim]")
                        if details.get("output"):
                            console.print("\n[bold]Test Output:[/bold]")
                            output_text = details["output"][:2000]
                            for line in output_text.split("\n")[:40]:
                                console.print(f"  {line}")
                        if details.get("warning"):
                            console.print(f"\n[yellow]Note: {details['warning']}[/yellow]")
                        console.print(f"\nTest files: {details.get('test_files', 0)}")
                        console.print(f"Test cases: ~{details.get('test_count', 0)}")

                    elif check.name == "linting":
                        if details.get("output"):
                            console.print("\n[bold]Linting Output:[/bold]")
                            output_text = details["output"][:2000]
                            for line in output_text.split("\n")[:50]:
                                if line.strip():
                                    console.print(f"  {line}")
                        if details.get("issues"):
                            console.print(f"\nTotal issues: {details['issues']}")

                    elif check.name == "security":
                        console.print(f"Files scanned: {details.get('files_scanned', 0)}")
                        if details.get("issues"):
                            console.print("\n[yellow]Issues found:[/yellow]")
                            for issue in details.get("issues", [])[:15]:
                                console.print(f"  [{issue.get('category')}] {issue.get('file')}")

                console.print()

        # Show security issues if any (non-verbose mode)
        if not verbose:
            for check in result.checks:
                if check.name == "security" and check.details and check.details.get("issues"):
                    console.print("\n[bold yellow]Security Issues Found:[/bold yellow]")
                    for issue in check.details["issues"][:5]:
                        console.print(f"  [{issue['category']}] {issue['file']}")

    except Exception as e:
        console.print(f"[red]✗[/red] Verification failed: {e}", style="bold red")
        sys.exit(1)


@cli.command()
@click.argument("repo_url")
@click.option("--wallet", required=True, help="Your Ethereum wallet address")
@click.option(
    "--network",
    type=click.Choice(["mainnet", "testnet", "localhost"]),
    default="testnet",
    help="Blockchain network",
)
@click.option("--standard-price", type=float, default=0.05, help="Price for standard license (ETH)")
@click.option("--premium-price", type=float, default=0.15, help="Price for premium license (ETH)")
@click.option(
    "--enterprise-price", type=float, default=0.50, help="Price for enterprise license (ETH)"
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json", "markdown"]),
    default="table",
    help="Output format",
)
def purchase_link(
    repo_url: str,
    wallet: str,
    network: str,
    standard_price: float,
    premium_price: float,
    enterprise_price: float,
    output_format: str,
):
    """
    Generate blockchain purchase links for a repository.

    Creates links to Story Protocol entries where buyers can purchase licenses.
    Links include:
    - Standard tier license
    - Premium tier license
    - Enterprise tier license
    """
    from rra.verification.blockchain_link import BlockchainLinkGenerator, NetworkType
    import json

    console.print(
        Panel.fit(
            f"[bold blue]Generating Purchase Links[/bold blue]\n{repo_url}", border_style="blue"
        )
    )

    try:
        network_type = NetworkType(network)
    except ValueError:
        network_type = NetworkType.TESTNET

    generator = BlockchainLinkGenerator(network=network_type)

    # Generate IP Asset ID
    ip_asset_id = generator.generate_ip_asset_id(repo_url, wallet)

    # Generate links
    pricing = {
        "standard": standard_price,
        "premium": premium_price,
        "enterprise": enterprise_price,
    }

    links = generator.generate_all_tier_links(
        repo_url=repo_url,
        ip_asset_id=ip_asset_id,
        pricing=pricing,
    )

    # Generate explorer link
    explorer_url = generator.generate_explorer_link(ip_asset_id)

    if output_format == "json":
        data = {
            "ip_asset_id": ip_asset_id,
            "explorer_url": explorer_url,
            "network": network,
            "links": [link.to_dict() for link in links],
        }
        console.print(json.dumps(data, indent=2))

    elif output_format == "markdown":
        md = f"""# Purchase Links for {repo_url.split('/')[-1]}

**IP Asset ID:** `{ip_asset_id}`
**Network:** {network}

## License Tiers

| Tier | Price | Purchase Link |
|------|-------|---------------|
"""
        for link in links:
            md += f"| {link.tier.value.capitalize()} | {link.price_display} | [{link.url}]({link.url}) |\n"

        md += f"""
## View on Story Protocol

[View IP Asset on Story Protocol Explorer]({explorer_url})

## Embed Widget

```html
{generator.generate_embed_widget(generator.generate_marketplace_listing(
    repo_url=repo_url,
    repo_name=repo_url.split("/")[-1],
    description="Software License",
    category="software",
    owner_address=wallet,
    pricing=pricing,
))}
```
"""
        console.print(Markdown(md))

    else:  # table format
        console.print(f"\n[bold]IP Asset ID:[/bold] [cyan]{ip_asset_id}[/cyan]")
        console.print(f"[bold]Network:[/bold] {network}")
        console.print(f"[bold]Explorer:[/bold] {explorer_url}\n")

        table = Table(title="Purchase Links", show_header=True)
        table.add_column("Tier", style="cyan", width=12)
        table.add_column("Price", style="green", width=12)
        table.add_column("URL", style="blue")

        for link in links:
            table.add_row(
                link.tier.value.capitalize(),
                link.price_display,
                link.url,
            )

        console.print(table)

        console.print("\n[bold]Quick Actions:[/bold]")
        console.print(f"  • Copy link for standard tier: {links[0].url}")
        console.print(f"  • View on explorer: {explorer_url}")


@cli.command()
@click.argument("repo_url")
@click.option(
    "--workspace",
    type=click.Path(path_type=Path),
    default=Path("./cloned_repos"),
    help="Directory for cloned repos",
)
def categorize(repo_url: str, workspace: Path):
    """
    Categorize a repository based on its structure and content.

    Analyzes the repository to determine:
    - Primary category (library, CLI, web app, API, etc.)
    - Subcategory (frontend, backend, ML, etc.)
    - Technologies used
    - Frameworks detected
    """

    console.print(
        Panel.fit(
            f"[bold blue]Categorizing Repository[/bold blue]\n{repo_url}", border_style="blue"
        )
    )

    try:
        # Clone and analyze
        with console.status("[bold blue]Analyzing repository...", spinner="dots"):
            ingester = RepoIngester(
                workspace_dir=workspace,
                verify_code=False,
                categorize=True,
                generate_blockchain_links=False,
            )
            kb = ingester.ingest(repo_url)

        if not kb.category:
            console.print("[yellow]Could not determine category[/yellow]")
            return

        # Display results
        category = kb.category
        confidence_color = (
            "green"
            if category.get("confidence", 0) > 0.7
            else ("yellow" if category.get("confidence", 0) > 0.4 else "red")
        )

        console.print(
            f"\n[bold]Primary Category:[/bold] [cyan]{category.get('primary_category', 'unknown')}[/cyan]"
        )
        if category.get("subcategory"):
            console.print(f"[bold]Subcategory:[/bold] {category.get('subcategory')}")
        console.print(
            f"[bold]Confidence:[/bold] [{confidence_color}]{category.get('confidence', 0):.0%}[/{confidence_color}]"
        )

        if category.get("technologies"):
            console.print("\n[bold]Technologies:[/bold]")
            for tech in category.get("technologies", []):
                console.print(f"  • {tech}")

        if category.get("frameworks"):
            console.print("\n[bold]Frameworks:[/bold]")
            for framework in category.get("frameworks", []):
                console.print(f"  • {framework}")

        if category.get("tags"):
            tags = ", ".join(category.get("tags", [])[:10])
            console.print(f"\n[bold]Tags:[/bold] {tags}")

        if category.get("reasoning"):
            console.print(f"\n[bold]Reasoning:[/bold] {category.get('reasoning')}")

    except Exception as e:
        console.print(f"[red]✗[/red] Categorization failed: {e}", style="bold red")
        sys.exit(1)


@cli.command()
@click.option("--history", "-n", default=10, help="Number of recent entries to show")
def dreaming(history: int):
    """
    Show dreaming status - what the system is doing.

    Displays recent activity and the current operation status.
    The dreaming status shows start and completion of operations,
    updating every 5 seconds to minimize overhead.
    """
    dreaming_status = get_dreaming_status()

    console.print(Panel.fit("[bold blue]Dreaming Status[/bold blue]", border_style="blue"))

    # Show current status
    current = dreaming_status.current_status
    if current:
        console.print(f"\n[bold]Current:[/bold] {current}")
    else:
        console.print("\n[bold]Current:[/bold] [dim]Idle[/dim]")

    # Show active operations
    active = dreaming_status.get_active_operations()
    if active:
        console.print("\n[bold]Active Operations:[/bold]")
        for op in active:
            console.print(f"  [blue]•[/blue] {op}")

    # Show history
    console.print()
    console.print(get_dreaming_summary(console))

    # Show configuration
    console.print(
        f"\n[dim]Throttle: {dreaming_status.throttle_seconds}s | "
        f"Enabled: {'Yes' if dreaming_status.enabled else 'No'}[/dim]"
    )


@cli.group()
def story():
    """
    Story Protocol integration commands.

    Register repositories as IP Assets, manage licenses, and track royalties
    on Story Protocol's programmable IP infrastructure.
    """
    pass


@story.command()
def status():
    """
    Show Story Protocol deployment status and network info.

    Displays contract addresses for all networks and validates connectivity.
    """
    from rra.contracts.story_protocol import StoryProtocolClient

    console.print(Panel.fit("[bold blue]Story Protocol Status[/bold blue]", border_style="blue"))

    # Get deployment status
    deployment = StoryProtocolClient.get_deployment_status()

    for network, contracts in deployment.items():
        all_deployed = all(contracts.values())
        status_icon = "[green]✓[/green]" if all_deployed else "[yellow]⚠[/yellow]"
        network_name = network.capitalize()

        if network == "mainnet":
            chain_info = "(Story Homer - Chain ID 1514)"
        elif network == "testnet":
            chain_info = "(Story Aeneid - Chain ID 1315)"
        else:
            chain_info = "(Local Foundry/Hardhat)"

        console.print(f"\n{status_icon} [bold]{network_name}[/bold] {chain_info}")

        table = Table(show_header=True, box=None, padding=(0, 2))
        table.add_column("Contract", style="cyan", width=25)
        table.add_column("Status", width=10)

        for contract_name, is_deployed in contracts.items():
            status_text = "[green]Ready[/green]" if is_deployed else "[red]Not Deployed[/red]"
            table.add_row(contract_name, status_text)

        console.print(table)

    # Show Story Protocol mainnet addresses
    console.print("\n[bold]Official Story Protocol Addresses (Mainnet):[/bold]")
    console.print("  IPAssetRegistry:   0x77319B4031e6eF1250907aa00018B8B1c67a244b")
    console.print("  LicensingModule:   0x04fbd8a2e56dd85CFD5500A4A4DfA955B9f1dE6f")
    console.print("  PILicenseTemplate: 0x2E896b0b2Fdb7457499B56AAaA4AE55BCB4Cd316")
    console.print("  RoyaltyModule:     0xD2f60c40fEbccf6311f8B47c4f2Ec6b040400086")

    console.print(
        "\n[dim]Source: https://docs.story.foundation/developers/deployed-smart-contracts[/dim]"
    )


@story.command()
@click.argument("repo_url")
@click.option("--wallet", required=True, help="Owner wallet address")
@click.option(
    "--private-key",
    envvar="STORY_PRIVATE_KEY",
    help="Private key for signing (or set STORY_PRIVATE_KEY env var)",
)
@click.option(
    "--network",
    type=click.Choice(["mainnet", "testnet", "localhost"]),
    default="testnet",
    help="Network to deploy on",
)
@click.option(
    "--rpc-url", envvar="STORY_RPC_URL", help="RPC endpoint URL (or set STORY_RPC_URL env var)"
)
@click.option("--description", help="Repository description for IP Asset metadata")
@click.option("--dry-run", is_flag=True, help="Simulate registration without executing")
def register(
    repo_url: str,
    wallet: str,
    private_key: Optional[str],
    network: str,
    rpc_url: Optional[str],
    description: Optional[str],
    dry_run: bool,
):
    """
    Register a repository as an IP Asset on Story Protocol.

    Creates an IP Asset entry on-chain and attaches PIL license terms
    based on your .market.yaml configuration.

    Example:
        rra story register https://github.com/user/repo --wallet 0x123... --network testnet

    Environment variables:
        STORY_PRIVATE_KEY: Your wallet's private key
        STORY_RPC_URL: Story Protocol RPC endpoint
    """
    from web3 import Web3
    from rra.integrations.story_integration import StoryIntegrationManager
    from rra.config.market_config import MarketConfig

    console.print(
        Panel.fit(
            f"[bold blue]Register IP Asset on Story Protocol[/bold blue]\n{repo_url}",
            border_style="blue",
        )
    )

    # Check prerequisites
    if not private_key and not dry_run:
        console.print(
            "[red]✗[/red] Private key required. Set STORY_PRIVATE_KEY env var or use --private-key"
        )
        console.print("  Example: export STORY_PRIVATE_KEY=0x...")
        sys.exit(1)

    # Set default RPC URLs
    if not rpc_url:
        if network == "mainnet":
            rpc_url = "https://mainnet.storyrpc.io"
        elif network == "testnet":
            rpc_url = "https://aeneid.storyrpc.io"
        else:
            rpc_url = "http://localhost:8545"

    console.print("\n[bold]Configuration:[/bold]")
    console.print(f"  Network: [cyan]{network}[/cyan]")
    console.print(f"  RPC URL: {rpc_url}")
    console.print(f"  Owner:   {wallet}")

    # Load market config
    try:
        config_path = Path(".market.yaml")
        if config_path.exists():
            # Parse the YAML manually to get story_protocol settings
            import yaml

            with open(config_path) as f:
                raw_config = yaml.safe_load(f)

            # Create a MarketConfig with the Story Protocol settings
            defi = raw_config.get("defi_integrations", {})
            story_config = defi.get("story_protocol", {})

            if not story_config.get("enabled", False):
                console.print("\n[yellow]⚠ Story Protocol not enabled in .market.yaml[/yellow]")
                console.print("  Set defi_integrations.story_protocol.enabled: true")

            # Build MarketConfig
            market_config = MarketConfig(
                target_price=raw_config.get("target_price", "0.05 ETH"),
                floor_price=raw_config.get("floor_price", "0.02 ETH"),
                story_protocol_enabled=story_config.get("enabled", True),
                pil_commercial_use=story_config.get("pil_terms", {}).get("commercial_use", True),
                pil_derivatives_allowed=story_config.get("pil_terms", {}).get(
                    "derivatives_allowed", True
                ),
                pil_derivatives_attribution=story_config.get("pil_terms", {}).get(
                    "derivatives_attribution", True
                ),
                pil_derivatives_reciprocal=story_config.get("pil_terms", {}).get(
                    "derivatives_reciprocal", False
                ),
                derivative_royalty_percentage=story_config.get(
                    "derivative_royalty_percentage", 0.15
                ),
                description=description or raw_config.get("description", f"Repository: {repo_url}"),
            )

            console.print("\n[bold]PIL Terms from .market.yaml:[/bold]")
            console.print(f"  Commercial Use:   {'✓' if market_config.pil_commercial_use else '✗'}")
            console.print(
                f"  Derivatives:      {'✓' if market_config.pil_derivatives_allowed else '✗'}"
            )
            console.print(
                f"  Attribution:      {'✓' if market_config.pil_derivatives_attribution else '✗'}"
            )
            console.print(
                f"  Royalty:          {(market_config.derivative_royalty_percentage or 0) * 100:.0f}%"
            )

        else:
            console.print("\n[yellow]⚠ No .market.yaml found, using defaults[/yellow]")
            market_config = MarketConfig(
                target_price="0.05 ETH",
                floor_price="0.02 ETH",
                story_protocol_enabled=True,
                description=description or f"Repository: {repo_url}",
            )

    except Exception as e:
        console.print(f"[red]✗[/red] Failed to load config: {e}")
        sys.exit(1)

    if dry_run:
        console.print("\n[yellow]DRY RUN - No transactions will be executed[/yellow]")
        console.print("\n[bold]Would execute:[/bold]")
        console.print("  1. Connect to Story Protocol network")
        console.print("  2. Register IP Asset with metadata")
        console.print("  3. Attach PIL license terms")
        console.print("  4. Configure royalty policy")
        console.print("  5. Update .market.yaml with IP Asset ID")
        console.print("\n[green]✓[/green] Dry run complete - configuration valid")
        return

    # Execute registration
    try:
        with console.status("[bold blue]Connecting to Story Protocol...", spinner="dots"):
            w3 = Web3(Web3.HTTPProvider(rpc_url))

            if not w3.is_connected():
                console.print(f"[red]✗[/red] Failed to connect to {rpc_url}")
                sys.exit(1)

            manager = StoryIntegrationManager(w3, network=network)

        console.print(f"[green]✓[/green] Connected to Story Protocol ({network})")

        with console.status("[bold blue]Registering IP Asset...", spinner="dots"):
            result = manager.register_repository_as_ip_asset(
                repo_url=repo_url,
                market_config=market_config,
                owner_address=wallet,
                private_key=private_key,
                repo_description=description,
            )

        if result.get("status") == "success":
            console.print("\n[green]✓ IP Asset Registered Successfully![/green]")
            console.print("\n[bold]Registration Details:[/bold]")
            console.print(f"  IP Asset ID: [cyan]{result['ip_asset_id']}[/cyan]")
            console.print(f"  TX Hash:     {result['tx_hash']}")
            console.print(f"  Block:       {result['block_number']}")

            if result.get("pil_terms_tx"):
                console.print(f"  PIL Terms TX: {result['pil_terms_tx']}")

            if result.get("royalty_tx"):
                console.print(f"  Royalty TX:  {result['royalty_tx']}")

            # Update .market.yaml
            if config_path.exists():
                with console.status("[bold blue]Updating .market.yaml...", spinner="dots"):
                    with open(config_path) as f:
                        raw_config = yaml.safe_load(f)

                    if "defi_integrations" not in raw_config:
                        raw_config["defi_integrations"] = {}
                    if "story_protocol" not in raw_config["defi_integrations"]:
                        raw_config["defi_integrations"]["story_protocol"] = {}

                    raw_config["defi_integrations"]["story_protocol"]["ip_asset_id"] = result[
                        "ip_asset_id"
                    ]

                    with open(config_path, "w") as f:
                        yaml.dump(raw_config, f, default_flow_style=False, sort_keys=False)

                console.print("[green]✓[/green] Updated .market.yaml with IP Asset ID")

            # Show explorer link
            if network == "mainnet":
                explorer = f"https://explorer.story.foundation/ip-asset/{result['ip_asset_id']}"
            else:
                explorer = f"https://aeneid.storyscan.xyz/ip-asset/{result['ip_asset_id']}"

            console.print("\n[bold]View on Explorer:[/bold]")
            console.print(f"  {explorer}")

        else:
            console.print(
                f"[red]✗[/red] Registration failed: {result.get('error', 'Unknown error')}"
            )
            sys.exit(1)

    except Exception as e:
        console.print(f"[red]✗[/red] Registration failed: {e}")
        sys.exit(1)


@story.command("info")
@click.argument("ip_asset_id")
@click.option(
    "--network",
    type=click.Choice(["mainnet", "testnet", "localhost"]),
    default="testnet",
    help="Network to query",
)
@click.option("--rpc-url", envvar="STORY_RPC_URL", help="RPC endpoint URL")
def story_info(ip_asset_id: str, network: str, rpc_url: Optional[str]):
    """
    Get information about an IP Asset on Story Protocol.

    Displays ownership, licensing terms, derivatives, and royalty information.
    """
    from web3 import Web3
    from rra.integrations.story_integration import StoryIntegrationManager

    console.print(
        Panel.fit(
            f"[bold blue]IP Asset Information[/bold blue]\n{ip_asset_id}", border_style="blue"
        )
    )

    # Set default RPC URLs
    if not rpc_url:
        if network == "mainnet":
            rpc_url = "https://mainnet.storyrpc.io"
        elif network == "testnet":
            rpc_url = "https://aeneid.storyrpc.io"
        else:
            rpc_url = "http://localhost:8545"

    try:
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        manager = StoryIntegrationManager(w3, network=network)

        # Get IP Asset info
        with console.status("[bold blue]Fetching IP Asset info...", spinner="dots"):
            asset_info = manager.story_client.get_ip_asset_info(ip_asset_id)

        console.print("\n[bold]IP Asset Details:[/bold]")
        console.print(f"  ID:       [cyan]{ip_asset_id}[/cyan]")
        console.print(f"  Owner:    {asset_info.get('owner', 'Unknown')}")
        console.print(f"  Active:   {'✓' if asset_info.get('is_active') else '✗'}")

        if asset_info.get("metadata"):
            console.print("\n[bold]Metadata:[/bold]")
            for key, value in asset_info.get("metadata", {}).items():
                console.print(f"  {key}: {value}")

        # Get royalty info
        with console.status("[bold blue]Fetching royalty info...", spinner="dots"):
            royalty_stats = manager.get_royalty_stats(ip_asset_id)

        console.print("\n[bold]Royalty Information:[/bold]")
        console.print(f"  Royalty Rate:    {royalty_stats.get('royalty_percentage', 0):.1f}%")
        console.print(f"  Total Collected: {royalty_stats.get('total_collected_eth', 0):.4f} ETH")

        # Get derivatives
        with console.status("[bold blue]Fetching derivatives...", spinner="dots"):
            derivatives = manager.get_repository_derivatives(ip_asset_id)

        console.print("\n[bold]Derivatives:[/bold]")
        console.print(f"  Count: {derivatives.get('derivative_count', 0)}")

        if derivatives.get("derivatives"):
            for deriv in derivatives.get("derivatives", [])[:5]:
                console.print(f"    • {deriv.get('id', 'Unknown')}")

    except Exception as e:
        console.print(f"[red]✗[/red] Failed to fetch info: {e}")
        sys.exit(1)


@story.command()
@click.argument("ip_asset_id")
@click.option(
    "--network",
    type=click.Choice(["mainnet", "testnet", "localhost"]),
    default="testnet",
    help="Network to query",
)
@click.option("--rpc-url", envvar="STORY_RPC_URL", help="RPC endpoint URL")
def royalties(ip_asset_id: str, network: str, rpc_url: Optional[str]):
    """
    Get royalty statistics for an IP Asset.

    Shows total collected royalties, payment history, and derivative contributions.
    """
    from web3 import Web3
    from rra.integrations.story_integration import StoryIntegrationManager
    from datetime import datetime

    console.print(
        Panel.fit(f"[bold blue]Royalty Statistics[/bold blue]\n{ip_asset_id}", border_style="blue")
    )

    # Set default RPC URLs
    if not rpc_url:
        if network == "mainnet":
            rpc_url = "https://mainnet.storyrpc.io"
        elif network == "testnet":
            rpc_url = "https://aeneid.storyrpc.io"
        else:
            rpc_url = "http://localhost:8545"

    try:
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        manager = StoryIntegrationManager(w3, network=network)

        with console.status("[bold blue]Fetching royalty stats...", spinner="dots"):
            stats = manager.get_royalty_stats(ip_asset_id)

        console.print("\n[bold]Royalty Overview:[/bold]")
        console.print(f"  IP Asset ID:     [cyan]{ip_asset_id}[/cyan]")
        console.print(f"  Royalty Rate:    {stats.get('royalty_percentage', 0):.1f}%")
        console.print(f"  Payment Token:   {stats.get('payment_token', 'ETH')}")

        console.print("\n[bold]Earnings:[/bold]")
        console.print(
            f"  Total Collected: [green]{stats.get('total_collected_eth', 0):.6f} ETH[/green]"
        )
        console.print(f"  Wei Amount:      {stats.get('total_collected_wei', 0)}")

        if stats.get("last_payment_timestamp"):
            last_payment = datetime.fromtimestamp(stats["last_payment_timestamp"])
            console.print(f"  Last Payment:    {last_payment.strftime('%Y-%m-%d %H:%M:%S')}")

    except Exception as e:
        console.print(f"[red]✗[/red] Failed to fetch royalty stats: {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli()
