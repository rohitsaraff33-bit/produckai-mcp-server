"""CLI commands for ProduckAI MCP Server."""

import json
import sys
from pathlib import Path

import click
import httpx
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from produckai_mcp.config import (
    Config,
    create_default_config,
    get_config,
    get_config_dir,
    save_default_config_template,
)

console = Console()


def get_claude_config_path() -> Path:
    """Get the Claude Desktop config file path."""
    if sys.platform == "darwin":  # macOS
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    elif sys.platform == "win32":  # Windows
        return Path.home() / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json"
    else:  # Linux
        return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"


@click.group()
@click.version_option(version="0.1.0", prog_name="produckai-mcp")
def cli():
    """ProduckAI MCP Server - Product feedback analysis integration for Claude Desktop."""
    pass


@cli.command()
@click.option(
    "--backend-url",
    default="http://localhost:8000",
    help="ProduckAI backend URL",
)
@click.option(
    "--skip-claude-config",
    is_flag=True,
    help="Skip Claude Desktop configuration",
)
def setup(backend_url: str, skip_claude_config: bool):
    """Set up ProduckAI MCP Server."""
    console.print(Panel.fit("🚀 ProduckAI MCP Server Setup", style="bold blue"))

    # Step 1: Create config directory
    config_dir = get_config_dir()
    console.print(f"\n[green]✓[/green] Config directory: {config_dir}")

    # Step 2: Create default configuration
    config = create_default_config()
    config.backend.url = backend_url
    config.save_to_file()
    console.print(f"[green]✓[/green] Configuration saved: {config_dir / 'config.yaml'}")

    # Step 3: Test backend connection
    console.print("\n[yellow]Testing backend connection...[/yellow]")
    try:
        response = httpx.get(f"{backend_url}/healthz", timeout=5.0)
        if response.status_code == 200:
            console.print(f"[green]✓[/green] Backend is reachable at {backend_url}")
        else:
            console.print(f"[yellow]⚠[/yellow] Backend responded with status {response.status_code}")
    except Exception as e:
        console.print(f"[red]✗[/red] Cannot reach backend: {str(e)}")
        console.print("\n[yellow]Please ensure ProduckAI backend is running:[/yellow]")
        console.print("  cd /path/to/produckai")
        console.print("  docker-compose up -d\n")

    # Step 4: Configure Claude Desktop (unless skipped)
    if not skip_claude_config:
        console.print("\n[yellow]Configuring Claude Desktop...[/yellow]")
        claude_config_path = get_claude_config_path()

        try:
            # Read existing config or create new
            if claude_config_path.exists():
                with open(claude_config_path, "r") as f:
                    claude_config = json.load(f)
            else:
                claude_config = {}

            # Ensure mcpServers section exists
            if "mcpServers" not in claude_config:
                claude_config["mcpServers"] = {}

            # Add ProduckAI server
            claude_config["mcpServers"]["produckai"] = {
                "command": sys.executable,  # Use current Python interpreter
                "args": ["-m", "produckai_mcp.server"],
            }

            # Ensure parent directory exists
            claude_config_path.parent.mkdir(parents=True, exist_ok=True)

            # Write config
            with open(claude_config_path, "w") as f:
                json.dump(claude_config, f, indent=2)

            console.print(f"[green]✓[/green] Claude Desktop configured: {claude_config_path}")
            console.print("\n[green]Setup complete![/green]")
            console.print("\n[bold]Next steps:[/bold]")
            console.print("  1. Restart Claude Desktop")
            console.print("  2. Look for ProduckAI tools in Claude")
            console.print("  3. Try: 'ping backend' to test the connection\n")

        except Exception as e:
            console.print(f"[red]✗[/red] Failed to configure Claude Desktop: {str(e)}")
            console.print("\n[yellow]Manual configuration:[/yellow]")
            console.print(f"Add this to {claude_config_path}:\n")
            console.print(json.dumps({
                "mcpServers": {
                    "produckai": {
                        "command": sys.executable,
                        "args": ["-m", "produckai_mcp.server"],
                    }
                }
            }, indent=2))
            console.print()
    else:
        console.print("\n[yellow]Skipped Claude Desktop configuration[/yellow]")
        console.print("Run without --skip-claude-config to configure automatically\n")


@cli.command()
def status():
    """Show current configuration and status."""
    console.print(Panel.fit("📊 ProduckAI MCP Server Status", style="bold blue"))

    # Load config
    try:
        config = get_config()
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to load configuration: {str(e)}")
        return

    # Configuration table
    config_table = Table(title="Configuration")
    config_table.add_column("Setting", style="cyan")
    config_table.add_column("Value", style="green")

    config_table.add_row("Backend URL", config.backend.url)
    config_table.add_row("Log Level", config.server.log_level)
    config_table.add_row("Log File", str(config.server.log_file) if config.server.log_file else "None")
    config_table.add_row("State Database", config.state.database)

    console.print(config_table)

    # Test backend
    console.print("\n[yellow]Testing backend connection...[/yellow]")
    try:
        response = httpx.get(f"{config.backend.url}/healthz", timeout=5.0)
        if response.status_code == 200:
            console.print(f"[green]✓[/green] Backend is healthy")
        else:
            console.print(f"[yellow]⚠[/yellow] Backend returned status {response.status_code}")
    except Exception as e:
        console.print(f"[red]✗[/red] Backend connection failed: {str(e)}")

    # Check Claude config
    console.print("\n[yellow]Checking Claude Desktop configuration...[/yellow]")
    claude_config_path = get_claude_config_path()
    if claude_config_path.exists():
        try:
            with open(claude_config_path, "r") as f:
                claude_config = json.load(f)
            if "mcpServers" in claude_config and "produckai" in claude_config["mcpServers"]:
                console.print(f"[green]✓[/green] ProduckAI server is configured in Claude Desktop")
            else:
                console.print(f"[yellow]⚠[/yellow] ProduckAI server not found in Claude Desktop config")
        except Exception as e:
            console.print(f"[red]✗[/red] Could not read Claude config: {str(e)}")
    else:
        console.print(f"[yellow]⚠[/yellow] Claude Desktop config not found at {claude_config_path}")


@cli.command()
@click.option(
    "--integration",
    type=click.Choice(["slack", "gdrive", "jira", "zoom", "all"]),
    default="all",
    help="Show status for specific integration",
)
def sync_status(integration: str):
    """Show sync status for integrations."""
    from produckai_mcp.state.database import Database
    from produckai_mcp.state.sync_state import SyncStateManager

    console.print(Panel.fit("🔄 Sync Status", style="bold blue"))

    try:
        config = get_config()
        db = Database(config.get_state_db_path())
        sync_state = SyncStateManager(db)

        if integration == "all":
            summary = sync_state.get_sync_summary()

            # Summary table
            summary_table = Table(title="Overall Summary")
            summary_table.add_column("Metric", style="cyan")
            summary_table.add_column("Value", style="green")

            summary_table.add_row("Total Resources", str(summary["total_resources"]))
            summary_table.add_row("Total Items Synced", str(summary["total_items_synced"]))

            console.print(summary_table)

            # Per-integration table
            if summary["by_integration"]:
                integration_table = Table(title="\nBy Integration")
                integration_table.add_column("Integration", style="cyan")
                integration_table.add_column("Resources", style="green")
                integration_table.add_column("Items", style="green")
                integration_table.add_column("Successful", style="green")
                integration_table.add_column("Failed", style="red")

                for integ, stats in summary["by_integration"].items():
                    integration_table.add_row(
                        integ.title(),
                        str(stats["resource_count"]),
                        str(stats["total_items"]),
                        str(stats["successful"]),
                        str(stats["failed"]),
                    )

                console.print(integration_table)

            # Recent failures
            if summary["recent_failures"]:
                console.print("\n[red]Recent Failures:[/red]")
                for failure in summary["recent_failures"][:5]:
                    console.print(f"  • {failure['integration']}:{failure['resource_name']} - {failure['error']}")
        else:
            # Show specific integration
            states = sync_state.get_all_sync_states(integration)

            if not states:
                console.print(f"[yellow]No sync history found for {integration}[/yellow]")
                return

            table = Table(title=f"{integration.title()} Sync History")
            table.add_column("Resource", style="cyan")
            table.add_column("Last Sync", style="green")
            table.add_column("Items", style="green")
            table.add_column("Status", style="green")

            for state in states:
                status_color = "green" if state["last_sync_status"] == "success" else "red"
                table.add_row(
                    state["resource_name"] or state["resource_id"],
                    state["last_sync_timestamp"] or "Never",
                    str(state["total_items_synced"]),
                    f"[{status_color}]{state['last_sync_status']}[/{status_color}]",
                )

            console.print(table)

    except Exception as e:
        console.print(f"[red]✗[/red] Error: {str(e)}")


@cli.command()
def reset():
    """Reset all configuration and state (destructive!)."""
    console.print("[red]⚠ WARNING: This will delete all configuration and sync state![/red]")
    if click.confirm("Are you sure you want to continue?"):
        config_dir = get_config_dir()

        # Delete config files
        config_file = config_dir / "config.yaml"
        if config_file.exists():
            config_file.unlink()
            console.print(f"[green]✓[/green] Deleted {config_file}")

        # Delete state database
        db_file = config_dir / "state.db"
        if db_file.exists():
            db_file.unlink()
            console.print(f"[green]✓[/green] Deleted {db_file}")

        console.print("\n[green]Reset complete![/green] Run 'produckai-mcp setup' to reconfigure.")
    else:
        console.print("Cancelled.")


def main():
    """Main CLI entry point."""
    cli()


if __name__ == "__main__":
    main()
