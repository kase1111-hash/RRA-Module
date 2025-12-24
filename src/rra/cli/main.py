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

import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown

from rra import __version__
from rra.config.market_config import MarketConfig, create_default_config, LicenseModel, NegotiationStyle
from rra.ingestion.repo_ingester import RepoIngester
from rra.agents.negotiator import NegotiatorAgent
from rra.agents.buyer import BuyerAgent


console = Console()


@click.group()
@click.version_option(version=__version__)
def cli():
    """
    RRA Module - Revenant Repo Agent

    Transform dormant repositories into autonomous licensing agents.
    """
    pass


@cli.command()
@click.argument('repo_path', type=click.Path(exists=True, path_type=Path))
@click.option('--target-price', default='0.05 ETH', help='Target price for licensing')
@click.option('--floor-price', default='0.02 ETH', help='Minimum acceptable price')
@click.option('--license-model', type=click.Choice(['per-seat', 'subscription', 'one-time', 'perpetual', 'custom']), default='per-seat')
@click.option('--negotiation-style', type=click.Choice(['concise', 'persuasive', 'strict', 'adaptive']), default='concise')
@click.option('--wallet', help='Ethereum wallet address for payments')
def init(
    repo_path: Path,
    target_price: str,
    floor_price: str,
    license_model: str,
    negotiation_style: str,
    wallet: Optional[str]
):
    """
    Initialize a repository with RRA configuration.

    Creates a .market.yaml file with the specified settings.
    """
    console.print(Panel.fit(
        f"[bold blue]Initializing RRA for repository[/bold blue]\n{repo_path}",
        border_style="blue"
    ))

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
@click.argument('repo_url')
@click.option('--workspace', type=click.Path(path_type=Path), default=Path('./cloned_repos'), help='Directory for cloned repos')
@click.option('--force', is_flag=True, help='Force refresh by re-cloning')
@click.option('--verify/--no-verify', default=True, help='Run code verification')
@click.option('--categorize/--no-categorize', default=True, help='Auto-categorize the repository')
@click.option('--wallet', help='Ethereum wallet address for blockchain links')
@click.option('--network', type=click.Choice(['mainnet', 'testnet', 'localhost']), default='testnet', help='Blockchain network')
def ingest(repo_url: str, workspace: Path, force: bool, verify: bool, categorize: bool, wallet: Optional[str], network: str):
    """
    Ingest a repository and generate its knowledge base.

    Clones the repository, parses its contents, and creates a structured
    knowledge base for agent reasoning.

    Now includes:
    - Code verification (tests, linting, security)
    - Automatic categorization
    - Blockchain purchase link generation
    """
    console.print(Panel.fit(
        f"[bold blue]Ingesting Repository[/bold blue]\n{repo_url}",
        border_style="blue"
    ))

    try:
        with console.status("[bold blue]Ingesting repository...", spinner="dots"):
            ingester = RepoIngester(
                workspace_dir=workspace,
                verify_code=verify,
                categorize=categorize,
                generate_blockchain_links=bool(wallet),
                owner_address=wallet,
                network=network,
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
            score = kb.verification.get('score', 0)
            status = kb.verification.get('overall_status', 'unknown')
            color = "green" if status == "passed" else ("yellow" if status == "warning" else "red")
            console.print(f"  Score: [{color}]{score}/100[/{color}]")
            console.print(f"  Status: [{color}]{status}[/{color}]")

            for check in kb.verification.get('checks', []):
                check_color = "green" if check['status'] == "passed" else ("yellow" if check['status'] == "warning" else "red")
                console.print(f"    [{check_color}]•[/{check_color}] {check['name']}: {check['message']}")

        # Show category
        if kb.category:
            console.print("\n[bold]Category:[/bold]")
            console.print(f"  Primary: [cyan]{kb.category.get('primary_category', 'unknown')}[/cyan]")
            if kb.category.get('subcategory'):
                console.print(f"  Subcategory: {kb.category.get('subcategory')}")
            if kb.category.get('tags'):
                tags = ', '.join(kb.category.get('tags', [])[:5])
                console.print(f"  Tags: {tags}")

        # Show blockchain links
        if kb.blockchain_links:
            console.print("\n[bold]Blockchain Links:[/bold]")
            console.print(f"  IP Asset ID: [cyan]{kb.blockchain_links.get('ip_asset_id')}[/cyan]")
            for link in kb.blockchain_links.get('purchase_links', []):
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
@click.argument('kb_path', type=click.Path(exists=True, path_type=Path))
@click.option('--interactive', is_flag=True, help='Start interactive negotiation session')
@click.option('--simulate', is_flag=True, help='Run simulation with buyer agent')
def agent(kb_path: Path, interactive: bool, simulate: bool):
    """
    Start a negotiation agent for a repository.

    Loads the knowledge base and starts an autonomous negotiation agent.
    """
    from rra.ingestion.knowledge_base import KnowledgeBase

    console.print(Panel.fit(
        f"[bold blue]Starting Negotiation Agent[/bold blue]",
        border_style="blue"
    ))

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

                if user_input.lower() in ['quit', 'exit', 'q']:
                    break

                # Get response
                response = negotiator.respond(user_input)
                console.print(f"\n[blue]Negotiator:[/blue] {response}\n")

            # Show summary
            summary = negotiator.get_negotiation_summary()
            console.print(f"\n[bold]Negotiation Summary:[/bold]")
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
@click.option('--workspace', type=click.Path(path_type=Path), default=Path('./agent_knowledge_bases'))
def list(workspace: Path):
    """
    List all ingested repositories and their knowledge bases.
    """
    if not workspace.exists():
        console.print("[yellow]No knowledge bases found[/yellow]")
        return

    kb_files = list(workspace.glob('*_kb.json'))

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

            repo_name = kb.repo_url.split('/')[-1]
            files = kb.statistics.get('code_files', 0)
            languages = ', '.join(kb.statistics.get('languages', [])[:3])
            updated = kb.updated_at.strftime('%Y-%m-%d')

            table.add_row(repo_name, str(files), languages, updated)
        except:
            pass

    console.print(table)


@cli.command()
@click.argument('kb_path', type=click.Path(exists=True, path_type=Path))
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

    console.print(Panel(
        Markdown(example_yaml),
        title="Example .market.yaml",
        border_style="blue"
    ))

    console.print("\n[bold]Quick Start:[/bold]")
    console.print("  1. Create .market.yaml in your repo root")
    console.print("  2. Run: rra init <repo-path>")
    console.print("  3. Customize the generated configuration")


@cli.command()
@click.argument('repo_url')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json', 'markdown']), default='table', help='Output format')
@click.option('--register', is_flag=True, help='Register the repository for permanent linking')
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

    console.print(Panel.fit(
        f"[bold blue]Generating Deep Links[/bold blue]\n{repo_url}",
        border_style="blue"
    ))

    service = DeepLinkService()

    # Register if requested
    if register:
        service.register_repo(repo_url)
        console.print(f"[green]✓[/green] Repository registered for permanent linking\n")

    # Get all links
    all_links = service.get_all_links(repo_url)

    if output_format == 'json':
        console.print(json.dumps(all_links, indent=2))

    elif output_format == 'markdown':
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

        table.add_row("Repository ID", all_links['repo_id'])
        table.add_row("Agent Page", all_links['agent_page'])
        table.add_row("Direct Chat", all_links['chat_direct'])
        table.add_row("Individual License", all_links['license_individual'])
        table.add_row("Team License", all_links['license_team'])
        table.add_row("Enterprise License", all_links['license_enterprise'])
        table.add_row("QR Code (PNG)", all_links['qr_code'])

        console.print(table)

        # Badge section
        console.print("\n[bold]README Badge (Markdown):[/bold]")
        console.print(Panel(all_links['badge_markdown'], border_style="dim"))

        # Embed section
        console.print("\n[bold]Embed Code (HTML):[/bold]")
        console.print(Panel(all_links['embed_script'], border_style="dim"))


@cli.command()
@click.argument('repo_id')
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
        console.print("\nThis ID may not be registered. Use 'rra links <repo-url> --register' to register a repository.")


@cli.command()
@click.argument('repo_url')
@click.option('--skip-tests', is_flag=True, help='Skip running actual tests')
@click.option('--skip-security', is_flag=True, help='Skip security scanning')
@click.option('--workspace', type=click.Path(path_type=Path), default=Path('./cloned_repos'), help='Directory for cloned repos')
def verify(repo_url: str, skip_tests: bool, skip_security: bool, workspace: Path):
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

    console.print(Panel.fit(
        f"[bold blue]Verifying Repository[/bold blue]\n{repo_url}",
        border_style="blue"
    ))

    try:
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

        verifier = CodeVerifier(skip_tests=skip_tests, skip_security=skip_security)

        readme_content = kb.documentation.get("README.md", "")

        result = verifier.verify(
            repo_path=kb.repo_path,
            repo_url=repo_url,
            readme_content=readme_content,
        )

        # Display results
        score = result.score
        status = result.overall_status.value
        status_color = "green" if status == "passed" else ("yellow" if status == "warning" else "red")

        console.print(f"[bold]Overall Score:[/bold] [{status_color}]{score}/100[/{status_color}]")
        console.print(f"[bold]Status:[/bold] [{status_color}]{status.upper()}[/{status_color}]")

        console.print("\n[bold]Detailed Checks:[/bold]\n")

        table = Table(show_header=True)
        table.add_column("Check", style="cyan", width=20)
        table.add_column("Status", width=10)
        table.add_column("Message", style="dim")

        for check in result.checks:
            check_color = "green" if check.status.value == "passed" else ("yellow" if check.status.value == "warning" else "red")
            status_icon = "✓" if check.status.value == "passed" else ("⚠" if check.status.value == "warning" else "✗")
            table.add_row(
                check.name.replace("_", " ").title(),
                f"[{check_color}]{status_icon} {check.status.value}[/{check_color}]",
                check.message[:60] + "..." if len(check.message) > 60 else check.message,
            )

        console.print(table)

        # Show security issues if any
        for check in result.checks:
            if check.name == "security" and check.details and check.details.get("issues"):
                console.print("\n[bold yellow]Security Issues Found:[/bold yellow]")
                for issue in check.details["issues"][:5]:
                    console.print(f"  [{issue['category']}] {issue['file']}")

    except Exception as e:
        console.print(f"[red]✗[/red] Verification failed: {e}", style="bold red")
        sys.exit(1)


@cli.command()
@click.argument('repo_url')
@click.option('--wallet', required=True, help='Your Ethereum wallet address')
@click.option('--network', type=click.Choice(['mainnet', 'testnet', 'localhost']), default='testnet', help='Blockchain network')
@click.option('--standard-price', type=float, default=0.05, help='Price for standard license (ETH)')
@click.option('--premium-price', type=float, default=0.15, help='Price for premium license (ETH)')
@click.option('--enterprise-price', type=float, default=0.50, help='Price for enterprise license (ETH)')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json', 'markdown']), default='table', help='Output format')
def purchase_link(repo_url: str, wallet: str, network: str, standard_price: float, premium_price: float, enterprise_price: float, output_format: str):
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

    console.print(Panel.fit(
        f"[bold blue]Generating Purchase Links[/bold blue]\n{repo_url}",
        border_style="blue"
    ))

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

    if output_format == 'json':
        data = {
            "ip_asset_id": ip_asset_id,
            "explorer_url": explorer_url,
            "network": network,
            "links": [link.to_dict() for link in links],
        }
        console.print(json.dumps(data, indent=2))

    elif output_format == 'markdown':
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
@click.argument('repo_url')
@click.option('--workspace', type=click.Path(path_type=Path), default=Path('./cloned_repos'), help='Directory for cloned repos')
def categorize(repo_url: str, workspace: Path):
    """
    Categorize a repository based on its structure and content.

    Analyzes the repository to determine:
    - Primary category (library, CLI, web app, API, etc.)
    - Subcategory (frontend, backend, ML, etc.)
    - Technologies used
    - Frameworks detected
    """
    from rra.verification.categorizer import CodeCategorizer

    console.print(Panel.fit(
        f"[bold blue]Categorizing Repository[/bold blue]\n{repo_url}",
        border_style="blue"
    ))

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
        confidence_color = "green" if category.get('confidence', 0) > 0.7 else ("yellow" if category.get('confidence', 0) > 0.4 else "red")

        console.print(f"\n[bold]Primary Category:[/bold] [cyan]{category.get('primary_category', 'unknown')}[/cyan]")
        if category.get('subcategory'):
            console.print(f"[bold]Subcategory:[/bold] {category.get('subcategory')}")
        console.print(f"[bold]Confidence:[/bold] [{confidence_color}]{category.get('confidence', 0):.0%}[/{confidence_color}]")

        if category.get('technologies'):
            console.print(f"\n[bold]Technologies:[/bold]")
            for tech in category.get('technologies', []):
                console.print(f"  • {tech}")

        if category.get('frameworks'):
            console.print(f"\n[bold]Frameworks:[/bold]")
            for framework in category.get('frameworks', []):
                console.print(f"  • {framework}")

        if category.get('tags'):
            tags = ', '.join(category.get('tags', [])[:10])
            console.print(f"\n[bold]Tags:[/bold] {tags}")

        if category.get('reasoning'):
            console.print(f"\n[bold]Reasoning:[/bold] {category.get('reasoning')}")

    except Exception as e:
        console.print(f"[red]✗[/red] Categorization failed: {e}", style="bold red")
        sys.exit(1)


if __name__ == '__main__':
    cli()
